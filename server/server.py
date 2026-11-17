"""Cybertank · servidor de partida (guerra de tanques 5 vs 5).

- Acepta hasta 10 jugadores por WebSocket (puerto 7654).
- Simula balas, impactos, vida, derribos y reapariciones a 20 ticks/s.
- Expone métricas Prometheus en :9100/metrics.
- Informa su ciclo de vida a Agones (/ready, /health, /shutdown).
- Opcional: envía los puntos de cada derribo a la tabla de líderes serverless
  (variable de entorno LEADERBOARD_URL).
"""
import asyncio
import json
import math
import os
import random
import time
import urllib.request

import websockets
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# ---------------------------------------------------------------- reglas del juego
MAX_JUGADORES = 12          # partida 5 vs 5
TICK_S = 0.05               # 20 ticks por segundo
ANCHO, ALTO = 1200, 800     # tamaño de la arena (px)
RADIO_TANQUE = 22
VIDA_MAX = 100
DANO_BALA = 25              # 4 impactos destruyen un tanque
VEL_BALA = 600.0            # px/s
VIDA_BALA_S = 1.5
CADENCIA_S = 0.4            # tiempo mínimo entre disparos
PUNTOS_DERRIBO = 100

# ---------------------------------------------------------------- métricas
JUGADORES = Gauge("cybertank_players_connected", "Jugadores conectados")
TICK = Histogram("cybertank_tick_seconds", "Duración del tick",
                 buckets=(.001, .0025, .005, .01, .025, .05, .1))
DISPAROS = Counter("cybertank_shots", "Disparos realizados")
DERRIBOS = Counter("cybertank_kills", "Tanques destruidos")

# ---------------------------------------------------------------- estado de la partida
estado = {}          # id -> tanque
balas = []           # balas en vuelo
ult_disparo = {}     # id -> instante del último disparo
conexiones = set()
partida = {"iniciada": False}
SDK = f"http://localhost:{os.getenv('AGONES_SDK_HTTP_PORT', '9358')}"
LEADERBOARD_URL = os.getenv("LEADERBOARD_URL", "")
_tareas = set()


def agones(ruta):
    """Llama al SDK REST de Agones (contenedor auxiliar). Fuera de Agones se ignora."""
    try:
        req = urllib.request.Request(SDK + ruta, data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass


def reportar_puntos(nombre, puntos):
    """Envía los puntos a la tabla de líderes serverless (práctica 3.5)."""
    if not LEADERBOARD_URL:
        return
    try:
        cuerpo = json.dumps({"jugador": nombre, "puntos": puntos}).encode()
        req = urllib.request.Request(LEADERBOARD_URL, data=cuerpo, method="POST",
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass


def limitar(v, minimo, maximo):
    return min(max(v, minimo), maximo)


def nuevo_tanque(tid, nombre):
    return {"id": tid, "nombre": str(nombre)[:16],
            "x": random.uniform(60, ANCHO - 60), "y": random.uniform(60, ALTO - 60),
            "a": 0.0, "vida": VIDA_MAX, "puntos": 0, "derribos": 0, "muertes": 0,
            "spawn": 0}


def reaparecer(t):
    """El tanque destruido reaparece en otro punto con vida completa."""
    t["vida"] = VIDA_MAX
    t["muertes"] += 1
    t["spawn"] += 1      # el cliente ve el cambio y se teletransporta
    t["x"] = random.uniform(60, ANCHO - 60)
    t["y"] = random.uniform(60, ALTO - 60)


def procesar_entrada(d, ahora=None):
    """Aplica el mensaje de un jugador: posición, ángulo de la torreta y disparo."""
    ahora = time.monotonic() if ahora is None else ahora
    tid = str(d["id"])
    t = estado.get(tid)
    if t is None:
        t = estado[tid] = nuevo_tanque(tid, d.get("nombre", tid))
    # Si el cliente aún no se enteró de su reaparición, se ignora su posición vieja.
    if d.get("spawn", t["spawn"]) == t["spawn"]:
        t["x"] = round(limitar(float(d.get("x", t["x"])), RADIO_TANQUE, ANCHO - RADIO_TANQUE), 1)
        t["y"] = round(limitar(float(d.get("y", t["y"])), RADIO_TANQUE, ALTO - RADIO_TANQUE), 1)
    t["a"] = round(float(d.get("a", t["a"])), 3)
    if d.get("dispara") and ahora - ult_disparo.get(tid, -1e9) >= CADENCIA_S:
        ult_disparo[tid] = ahora
        cos_a, sin_a = math.cos(t["a"]), math.sin(t["a"])
        balas.append({"x": t["x"] + cos_a * (RADIO_TANQUE + 6),
                      "y": t["y"] + sin_a * (RADIO_TANQUE + 6),
                      "vx": cos_a * VEL_BALA, "vy": sin_a * VEL_BALA,
                      "vida": VIDA_BALA_S, "dueno": tid})
        DISPAROS.inc()
    return tid


def avanzar(dt):
    """Mueve las balas y resuelve impactos. Devuelve [(atacante, victima), ...]."""
    derribados = []
    vivas = []
    for b in balas:
        b["x"] += b["vx"] * dt
        b["y"] += b["vy"] * dt
        b["vida"] -= dt
        if b["vida"] <= 0 or not (0 <= b["x"] <= ANCHO and 0 <= b["y"] <= ALTO):
            continue
        impacto = None
        for t in estado.values():
            if t.get("id") == b["dueno"] or "vida" not in t:
                continue
            if (t["x"] - b["x"]) ** 2 + (t["y"] - b["y"]) ** 2 <= RADIO_TANQUE ** 2:
                impacto = t
                break
        if impacto is None:
            vivas.append(b)
            continue
        impacto["vida"] -= DANO_BALA
        if impacto["vida"] <= 0:
            atacante = estado.get(b["dueno"])
            if atacante:
                atacante["puntos"] += PUNTOS_DERRIBO
                atacante["derribos"] += 1
            reaparecer(impacto)
            DERRIBOS.inc()
            derribados.append((b["dueno"], impacto["id"]))
    balas[:] = vivas
    return derribados


def snapshot():
    return json.dumps({"t": time.time(), "e": estado,
                       "b": [[round(b["x"]), round(b["y"])] for b in balas]})


async def jugador(ws):
    if len(conexiones) >= MAX_JUGADORES:
        await ws.close(code=4000, reason="partida llena")
        return
    conexiones.add(ws)
    JUGADORES.set(len(conexiones))
    partida["iniciada"] = True
    mi_id = None
    try:
        async for msg in ws:
            try:
                d = json.loads(msg)
            except ValueError:
                continue
            if "ping" in d:                        # medición de latencia: responde al instante
                await ws.send(json.dumps({"pong": d["ping"]}))
            elif "id" in d:                        # posición, torreta y disparo del tanque
                mi_id = procesar_entrada(d)
    finally:
        conexiones.discard(ws)
        JUGADORES.set(len(conexiones))
        estado.pop(mi_id, None)                    # el tanque sale de la arena
        ult_disparo.pop(mi_id, None)


def _enviar_puntos_en_segundo_plano(nombre):
    tarea = asyncio.create_task(asyncio.to_thread(reportar_puntos, nombre, PUNTOS_DERRIBO))
    _tareas.add(tarea)
    tarea.add_done_callback(_tareas.discard)


async def bucle():
    n = 0
    ultimo = time.perf_counter()
    while True:
        t = time.perf_counter()
        dt, ultimo = t - ultimo, t
        for atacante, _ in avanzar(dt):
            if LEADERBOARD_URL and atacante in estado:
                _enviar_puntos_en_segundo_plano(estado[atacante]["nombre"])
        if conexiones:
            websockets.broadcast(conexiones, snapshot())
        TICK.observe(time.perf_counter() - t)
        n += 1
        if n % 40 == 0:                            # latido a Agones cada 2 s
            await asyncio.to_thread(agones, "/health")
        if partida["iniciada"] and not conexiones:
            await asyncio.to_thread(agones, "/shutdown")   # fin de partida
            partida["iniciada"] = False
        await asyncio.sleep(max(0.0, TICK_S - (time.perf_counter() - t)))


async def main():
    start_http_server(9100)                        # /metrics para Prometheus
    async with websockets.serve(jugador, "0.0.0.0", 7654):
        print("Cybertank escuchando en :7654 (métricas en :9100/metrics)", flush=True)
        agones("/ready")                           # listo para recibir una partida
        await bucle()


if __name__ == "__main__":
    asyncio.run(main())
