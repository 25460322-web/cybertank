"""Práctica 3.4 / 3.5 · Jugadores, espectadores y tabla de líderes simulados con Locust.

Jugador     → pide un GameServer al allocator de Agones (o usa SERVIDOR_FIJO), abre un
              WebSocket, mueve su tanque y dispara 20 veces/s, mide RTT con ping 1 vez/s.
Espectador  → descarga el stream HLS desde CloudFront como un reproductor (--host CDN).
Lider       → 80 % lecturas del top 10 y 20 % escrituras (--host URL de la API).

Ejemplos:
  SERVIDOR_FIJO=localhost:7654 locust -f locustfile.py Jugador -u 9 -r 3        (prueba local)
  ALLOCATOR_HOST=<host> locust -f locustfile.py Jugador -u 1000 -r 2 -t 20m --headless --csv rampa
"""
import json
import math
import os
import random
import time
import uuid

import requests
import urllib3
from gevent.lock import Semaphore
from locust import HttpUser, User, between, constant, constant_pacing, events, task
from locust.exception import StopUser
from websocket import create_connection          # pip install websocket-client

ALLOCATOR = f"https://{os.environ.get('ALLOCATOR_HOST', '')}/gameserverallocation"
SERVIDOR_FIJO = os.environ.get("SERVIDOR_FIJO", "")      # p. ej. localhost:7654
PEDIDO = {"namespace": "default",
          "gameServerSelectors": [{"matchLabels": {"agones.dev/fleet": "cybertank-fleet"}}]}
# En EKS el allocator queda detrás de un nombre DNS de ELB que no está en su certificado:
# en el laboratorio se desactiva la verificación (VERIFICAR_TLS=1 para activarla).
VERIFICAR = "ca.crt" if os.environ.get("VERIFICAR_TLS") == "1" else False
if not VERIFICAR:
    urllib3.disable_warnings()
CERTS = {"cert": ("client.crt", "client.key"), "verify": VERIFICAR}


def medir(nombre, inicio, error=None):
    events.request.fire(request_type="WS", name=nombre,
                        response_time=(time.perf_counter() - inicio) * 1000,
                        response_length=0, exception=error)


class Jugador(User):
    wait_time = constant(0.05)                    # 20 mensajes por segundo
    sala = {"addr": None, "cupo": 0}              # mini-matchmaker compartido
    candado = Semaphore()

    def pedir_servidor(self):
        if SERVIDOR_FIJO:
            return SERVIDOR_FIJO
        with Jugador.candado:                     # un solo pedido a la vez
            if Jugador.sala["cupo"] == 0:         # sala llena: pide otro servidor
                t0 = time.perf_counter()
                try:
                    r = requests.post(ALLOCATOR, json=PEDIDO, timeout=10, **CERTS)
                    r.raise_for_status()
                    gs = r.json()
                    medir("asignacion", t0)
                except Exception as e:
                    medir("asignacion", t0, e)
                    raise
                Jugador.sala = {"addr": f"{gs['address']}:{gs['ports'][0]['port']}", "cupo": 10}
            Jugador.sala["cupo"] -= 1
            return Jugador.sala["addr"]

    def on_start(self):
        self.ws = None
        self.id, self.n = "bot-" + uuid.uuid4().hex[:6], 0
        self.x, self.y = random.uniform(60, 1140), random.uniform(60, 740)
        self.a = random.uniform(-math.pi, math.pi)
        # Como un jugador real en el matchmaking: si no hay servidor Ready (429 del allocator
        # mientras el autoscaler crea nodos), espera y reintenta en vez de abandonar.
        for _ in range(60):
            t0 = time.perf_counter()
            try:
                self.ws = create_connection(f"ws://{self.pedir_servidor()}", timeout=5)
                medir("conexion", t0)
                return
            except Exception as e:
                medir("conexion", t0, e)
                time.sleep(2)                     # gevent lo vuelve no bloqueante
        raise StopUser()

    @task
    def jugar(self):
        if not self.ws:
            return
        self.x = min(1178, max(22, self.x + random.uniform(-6, 6)))
        self.y = min(778, max(22, self.y + random.uniform(-6, 6)))
        self.a += random.uniform(-0.2, 0.2)
        try:
            self.ws.send(json.dumps({"id": self.id, "nombre": self.id, "x": self.x, "y": self.y,
                                     "a": self.a, "dispara": random.random() < 0.1}))
        except Exception as e:                    # el servidor se cerró: vuelve al matchmaking
            medir("envio", time.perf_counter(), e)
            self.on_start()
            return
        self.n += 1
        if self.n % 20 == 0:                      # un ping por segundo
            t0 = time.perf_counter()
            try:
                self.ws.send(json.dumps({"ping": t0}))
                while json.loads(self.ws.recv()).get("pong") != t0:
                    pass                          # descarta los snapshots acumulados
                medir("rtt", t0)
            except Exception as e:
                medir("rtt", t0, e)

    def on_stop(self):
        if getattr(self, "ws", None):
            self.ws.close()


class Espectador(HttpUser):
    wait_time = constant_pacing(2)                # un segmento cada 2 s, como el reproductor

    def on_start(self):
        self.i = random.randint(0, 100)           # cada espectador empieza en otro punto

    @task
    def ver_stream(self):
        m = self.client.get("/live/cybertank/360p.m3u8", name="manifiesto")
        segmentos = [l for l in m.text.splitlines() if l.endswith(".ts")]
        if not segmentos:
            return
        seg = segmentos[self.i % len(segmentos)]
        self.i += 1
        with self.client.get(f"/live/cybertank/{seg}", name="segmento", catch_response=True) as r:
            if r.elapsed.total_seconds() > 2:
                r.failure("rebuffering: el segmento tardó más de lo que dura")


class Lider(HttpUser):
    """Prueba de carga de la tabla de líderes (práctica 3.5): 80 % lecturas, 20 % escrituras."""
    wait_time = between(0.5, 1.5)

    @task(8)
    def leer_top(self):
        self.client.get("/", name="GET top10")

    @task(2)
    def registrar(self):
        self.client.post("/", json={"jugador": f"bot-{random.randint(1, 500)}",
                                    "puntos": random.choice([100, 200, 300])}, name="POST puntos")
