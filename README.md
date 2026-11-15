# Cybertank

Juego de guerra de tanques 5 vs 5 desplegado en AWS: servidor de partida en contenedores
orquestado con EKS + Agones, autoescalado en tres capas, tabla de líderes serverless,
pipeline CI/CD con GitHub Actions e infraestructura completa en Terraform.

**👉 Sigue [GUIA.md](GUIA.md) paso a paso**: incluye todos los comandos y las 80 capturas para documentar la Unidad 3.

## Arquitectura

```
Jugadores (navegador) ──WebSocket──► Flota de GameServers (Agones en EKS, nodos c7i)
        │                                   │ /metrics          │ puntos por derribo
        │                                   ▼                   ▼
        │                         Prometheus + Grafana    API Gateway → Lambda → DynamoDB
        └──── top 10 global ─────────────────────────────────────┘
Espectadores ──HLS──► CloudFront ──► S3
GitHub Actions ──OIDC──► ECR ──► kubectl apply (drenado de partidas)
Terraform ──► VPC, EKS, ECR, Agones, Cluster Autoscaler, Lambda, DynamoDB, API Gateway
```

## Prueba rápida en local

```bash
cd server && pip install -r requirements.txt pytest && pytest -q && python server.py
# abre client/index.html en dos pestañas del navegador
```
