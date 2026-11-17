# Práctica 3.5 · Resultados (16-nov-2026, us-east-2)

Todo se creó por AWS CLI (no hay acceso a la consola web de la cuenta del proyecto).

| Recurso | Nombre |
|---|---|
| DynamoDB (on-demand, clave `jugador`) | `cybertank-scores` |
| Lambda Python 3.12, 256 MB | `cybertank-leaderboard` |
| Rol (inline: `UpdateItem` + `Scan` solo en la tabla; logs) | `cybertank-leaderboard-rol` |
| API Gateway HTTP API (payload 2.0, CORS `*`) | `https://u1ekizj1z8.execute-api.us-east-2.amazonaws.com` |

## Integración con el juego
`LEADERBOARD_URL` en `k8s/fleet.yaml` → desplegado por el pipeline (3.2). Cada derribo suma 100
puntos: servidor en EKS → API Gateway → Lambda → DynamoDB → Top 10 en el cliente (C60).

**Hallazgo:** abierto como `file://`, el navegador envía `Origin: null` y API Gateway no devuelve
`Access-Control-Allow-Origin` → "Error al leer la tabla". Servido desde `http://localhost:8080`
funciona. En producción el cliente debe publicarse en un dominio (S3 + CloudFront).

## Prueba de carga (500 usuarios, 80 % GET / 20 % POST, 3 min, arranque en frío forzado)
| Métrica | Valor | Fuente |
|---|---|---|
| Peticiones / fallas | 49 026 / **0** (sin 429 ni 503) | C61 |
| Duración real en Lambda | promedio **≈ 50 ms**, máximo 336 ms | C62 |
| Concurrencia máxima | **100** (límite de la cuenta: 400) | C62 |
| Arranques en frío | **77**, *Init Duration* promedio **480 ms** (máx. 563 ms) | C63 |
| p95 visto por Locust | 3.4 s → **inflado por el generador** (Locust en Windows = 1 núcleo, 500 usuarios); Lambda midió ~50 ms | C61 vs C62 |

El arranque en frío se forzó cambiando una variable de entorno (Lambda descarta las instancias
calientes) en lugar de esperar 15 minutos.

## Costo mensual (5 M peticiones, 50 ms, 256 MB) — `loadtest/costo_serverless.py`, C64
| | USD/mes |
|---|---|
| Lambda + API Gateway HTTP + DynamoDB | **8.67** (7.42 con capa gratuita) |
| EC2 t3.small 24x7 | **15.18** |

Serverless es más barato hasta ≈ 9 M peticiones/mes, escala solo y no cobra sin tráfico.
Mejora sugerida: el GET hace `Scan` de toda la tabla; con muchos jugadores conviene un índice
secundario global por puntos o cachear el top 10 unos segundos.
