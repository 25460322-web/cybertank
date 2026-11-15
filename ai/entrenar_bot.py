"""Práctica 3.1 · Entrenar y servir el bot artillero de Cybertank.

Entorno didáctico ApuntarTanque: el bot controla la torreta y debe girarla hacia
un tanque enemigo que se mueve, y disparar solo cuando está alineado.

Uso (Colab o SageMaker Studio Lab con GPU):
    pip install -r requirements.txt
    python entrenar_bot.py --pasos 100000
"""
import argparse
import math
import time

import gymnasium as gym
import numpy as np
import torch
from gymnasium import spaces
from stable_baselines3 import PPO


class ApuntarTanque(gym.Env):
    """Observación: [sin(dif), cos(dif), distancia]. Acciones: 0 izq, 1 der, 2 disparar."""

    GIRO = 0.15          # rad por paso
    TOLERANCIA = 0.12    # rad: el disparo acierta si la torreta está dentro de este ángulo

    def __init__(self):
        self.observation_space = spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32)
        self.action_space = spaces.Discrete(3)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.torreta = self.np_random.uniform(-math.pi, math.pi)
        self.pasos = 0
        self._nuevo_enemigo()
        return self._obs(), {}

    def _nuevo_enemigo(self):
        self.enemigo = self.np_random.uniform(-math.pi, math.pi)
        self.distancia = self.np_random.uniform(0.2, 1.0)

    def _dif(self):
        return (self.enemigo - self.torreta + math.pi) % (2 * math.pi) - math.pi

    def _obs(self):
        d = self._dif()
        return np.array([math.sin(d), math.cos(d), self.distancia], dtype=np.float32)

    def step(self, accion):
        self.pasos += 1
        recompensa = -0.01                     # el tiempo cuesta: apunta rápido
        info = {"acierto": False}
        if accion == 0:
            self.torreta -= self.GIRO
        elif accion == 1:
            self.torreta += self.GIRO
        elif abs(self._dif()) < self.TOLERANCIA:
            recompensa += 1.0
            info["acierto"] = True
            self._nuevo_enemigo()
        else:
            recompensa -= 0.2                  # disparo fallado
        self.enemigo += self.np_random.normal(0, 0.03)   # el enemigo se mueve
        return self._obs(), recompensa, False, self.pasos >= 200, info


def aciertos_por_episodio(politica, episodios=20):
    env = ApuntarTanque()
    total = 0
    for ep in range(episodios):
        obs, _ = env.reset(seed=ep)
        fin = False
        while not fin:
            obs, _, term, trunc, info = env.step(politica(obs))
            total += info["acierto"]
            fin = term or trunc
    return total / episodios


def entrenar(device, pasos):
    modelo = PPO("MlpPolicy", ApuntarTanque(), verbose=0, device=device, seed=0)
    inicio = time.time()
    modelo.learn(total_timesteps=pasos)
    return modelo, time.time() - inicio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasos", type=int, default=100_000)
    ap.add_argument("--bots", type=int, default=2000)
    ap.add_argument("--hz", type=int, default=10)
    args = ap.parse_args()

    azar = aciertos_por_episodio(lambda o: np.random.randint(3))
    print(f"Bot al azar: {azar:.1f} aciertos por episodio")

    modelo, t_cpu = entrenar("cpu", args.pasos)
    print(f"Entrenamiento CPU: {t_cpu:.1f} s")
    t_gpu = None
    if torch.cuda.is_available():
        _, t_gpu = entrenar("cuda", args.pasos)
        print(f"Entrenamiento GPU ({torch.cuda.get_device_name(0)}): {t_gpu:.1f} s")
    else:
        print("GPU no disponible: activa 'Entorno de ejecución → GPU T4' en Colab")

    entrenado = aciertos_por_episodio(lambda o: int(modelo.predict(o, deterministic=True)[0]))
    print(f"Bot entrenado: {entrenado:.1f} aciertos por episodio")
    modelo.save("bot_cybertank")

    # Latencia de inferencia en CPU (una decisión por llamada, como en el servidor)
    env = ApuntarTanque()
    obs, _ = env.reset(seed=1)
    n = 10_000
    t = time.perf_counter()
    for _ in range(n):
        modelo.predict(obs, deterministic=True)
    lat_ms = (time.perf_counter() - t) / n * 1000
    por_nucleo = 1000 / lat_ms

    demanda = args.bots * args.hz
    vcpu = demanda / por_nucleo
    vcpu_margen = math.ceil(vcpu * 1.3)

    print("\n=========== TABLA PARA EL ENTREGABLE 3.1 ===========")
    print(f"| Métrica                         | Valor            |")
    print(f"|---------------------------------|------------------|")
    print(f"| Entrenamiento CPU ({args.pasos} pasos) | {t_cpu:8.1f} s       |")
    print(f"| Entrenamiento GPU               | {('%.1f s' % t_gpu) if t_gpu else 'sin GPU':>16} |")
    print(f"| Aciertos/episodio azar → bot    | {azar:5.1f} → {entrenado:5.1f}    |")
    print(f"| Latencia de inferencia (CPU)    | {lat_ms:8.3f} ms      |")
    print(f"| Decisiones/s por núcleo         | {por_nucleo:10,.0f}       |")
    print(f"| Demanda {args.bots} bots × {args.hz} Hz      | {demanda:10,} inf/s |")
    print(f"| vCPU necesarias (+30 % margen)  | {vcpu:.1f} → {vcpu_margen} vCPU     |")
    print("=====================================================")
    print("Costo: multiplica las vCPU por el precio/hora de c7i (calculator.aws).")


if __name__ == "__main__":
    main()
