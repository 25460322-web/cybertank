"""Práctica 3.4 · Paso 5: curva CCU vs latencia p95 y resumen de la prueba.

Uso: python analizar.py rampa         (lee rampa_stats_history.csv y rampa_stats.csv)
"""
import sys

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

prefijo = sys.argv[1] if len(sys.argv) > 1 else "rampa"
META_MS = 80

h = pd.read_csv(f"{prefijo}_stats_history.csv")
h = h[h["Name"] == "Aggregated"].copy()
h["p95"] = pd.to_numeric(h["95%"], errors="coerce")
h = h.dropna(subset=["p95"])

plt.figure(figsize=(8, 4.5))
plt.plot(h["User Count"], h["p95"], label="p95 medido")
plt.axhline(META_MS, linestyle="--", color="tab:red", label=f"meta p95 = {META_MS} ms")
plt.xlabel("Jugadores simulados (CCU)")
plt.ylabel("Latencia p95 (ms)")
plt.title(f"Cybertank · CCU vs latencia p95 ({prefijo})")
plt.legend()
plt.grid(alpha=.3)
plt.tight_layout()
plt.savefig(f"{prefijo}_ccu_vs_p95.png", dpi=150)

cruce = h[h["p95"] > META_MS]
print(f"Gráfica guardada en {prefijo}_ccu_vs_p95.png")
print(f"CCU máximo alcanzado: {int(h['User Count'].max())}")
if cruce.empty:
    print(f"La p95 nunca superó {META_MS} ms: la capacidad real es mayor que la carga probada.")
else:
    print(f"La p95 cruzó {META_MS} ms con {int(cruce['User Count'].iloc[0])} jugadores "
          "→ esa es la capacidad real; divídela entre los nodos activos en ese momento.")

s = pd.read_csv(f"{prefijo}_stats.csv")
print("\nResumen por petición:")
print(s[["Type", "Name", "Request Count", "Failure Count", "Median Response Time",
         "95%", "99%"]].to_string(index=False))
