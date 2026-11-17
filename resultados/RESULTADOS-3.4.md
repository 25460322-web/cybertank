# Práctica 3.4 · Resultados (16-nov-2026, us-east-2)

## Entorno real (limitado por la cuenta de la escuela, plan gratuito)
| | Guía | Usado | Motivo |
|---|---|---|---|
| Nodos de juego | c7i.xlarge (4 vCPU) | **c7i-flex.large** (2 vCPU, 4 GiB) | solo tipos *free-tier-eligible* |
| Generador de carga | c7i.2xlarge (8 vCPU) | **c7i-flex.large** (2 vCPU) | ídem |
| Jugadores simulados | 1 000 | **300** | el generador de 2 vCPU se satura a ~200–300 |
| Stream de prueba | FFmpeg local | FFmpeg en Docker (`linuxserver/ffmpeg`) | instalar FFmpeg con winget se colgaba |

## Hallazgos
1. **Bug encontrado por la prueba de carga** (C43): el servidor enviaba `/ready` a Agones una sola vez.
   Con nodos al 94 % de CPU el sidecar del SDK tardaba en arrancar, el aviso se perdía y el
   GameServer se quedaba en *Scheduled* para siempre → 0 servidores Ready y el allocator devolvía
   **429 Too Many Requests** aunque había nodos libres. Corrección: reintentar `/ready` cada 0.5 s
   (commit `2704f73`, con prueba unitaria) desplegada por el pipeline de la 3.2.
2. **Buffer agotado**: con `bufferSize: 20%` y la revisión por omisión del FleetAutoscaler
   (cada 30 s) la carga se comía los Ready antes de reponerlos (rampa: 552 asignaciones con 429).
   Ajuste (`k8s/fleetautoscaler-ajustado.yaml`): **30 %, mínimo 5, revisión cada 5 s** →
   en el pico los 429 bajaron a 107 y quedaron 13 servidores Ready de reserva (C48, C49).
3. **Cluster Autoscaler**: escaló 3 → 4 → 5 → 6 → 9 → 12 nodos (máximo) y luego bajó solo (C44, C45).

## Números para el entregable
| Métrica | Valor | Fuente |
|---|---|---|
| RTT del juego p50 / p95 (rampa de capacidad) | 11 ms / 200 ms | `capacidad_stats.csv` |
| **CCU donde la p95 cruza 80 ms** | **149 jugadores** con **3 nodos** activos | C52, `escalado.log` 19:51 |
| **Capacidad por nodo c7i-flex.large** | **≈ 50 jugadores (5 partidas de 10)** | 149 ÷ 3 |
| Pico: 300 jugadores en 20 s | 30 servidores asignados en ≈ 45 s, RTT p95 160 ms, 0 fallas de rtt | C49 |
| Tiempo de reacción del Cluster Autoscaler | ≈ 45–60 s (Ready agotados 19:51:02 → nodo nuevo 19:51:46) | `escalado.log` |
| Duración del tick p99 | 1–3.3 ms (meta < 25 ms) | Grafana C43/C48 |
| 500 espectadores 360p, 4 min | 118 000 descargas, **0 fallas**, segmento p99 470 ms (< 2 s: sin rebuffering) | C50 |
| Egress medido por CloudWatch | **12.00 GB** = fórmula `egress.py` (12 GB) | C51, C53 |
| Extrapolación 20 000 espectadores 1080p, 1 h | 54 TB ≈ **USD 4 315** | C53 |

## Recomendación
- **FleetAutoscaler**: `bufferSize` 30 % (o absoluto ≥ 5), `minReplicas` 5, `sync` cada 5 s.
- **Máquina**: con c7i-flex.large caben ~5 partidas por nodo; en producción conviene c7i.xlarge
  (≈ 10 partidas por nodo y menos overhead de DaemonSets por jugador).
- **Mínimo de nodos**: 3 (cubre 150 jugadores sin esperar al Cluster Autoscaler, que tarda ~1 min).
- **Generador de carga**: ≥ 8 vCPU para pasar de 300 jugadores simulados (con 2 vCPU el propio
  Locust infla la latencia medida).
- **Streaming**: el egress domina el costo (54 TB/h a 1080p); usar ABR (360p/720p) y la capa gratuita.
