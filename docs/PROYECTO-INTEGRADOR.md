# Cybertank · Proyecto integrador "Día de lanzamiento"

Juego de tanques 5 vs 5 en tiempo real desplegado en AWS (us-east-2, Ohio).
Repositorio: <https://github.com/25460322-web/cybertank>

## 1. Arquitectura

```
 Jugador (navegador, canvas)                         Espectador (HLS)
   │  WebSocket ws://IP-nodo:7000-8000                   │ https
   ▼                                                     ▼
 ┌──────────── EKS cybertank-default (Terraform) ────┐  CloudFront ─(OAC)→ S3 (segmentos .ts)
 │  Agones Fleet "cybertank-fleet" (GameServers)     │
 │   └─ pod: servidor Python (20 ticks/s, 10 jug.)   │
 │        ├─ SDK sidecar (/ready /health /shutdown)  │
 │        └─ :9100/metrics ──→ Prometheus → Grafana  │
 │  Agones allocator (mTLS, ELB) ← Locust / matchmaker│
 │  FleetAutoscaler (buffer)  +  Cluster Autoscaler  │
 │  Nodos c7i-flex.large en subredes públicas (sin NAT)
 └──────────────┬────────────────────────────────────┘
                │ POST puntos por derribo
                ▼
   API Gateway HTTP API → Lambda (Python 3.12) → DynamoDB (on-demand)  ← GET top 10 (cliente)

 GitHub Actions: pytest → docker build → ECR (etiqueta = SHA) → aprobación manual → kubectl apply
 Terraform: VPC, EKS, node group, reglas 7000-8000, ECR, Agones, Cluster Autoscaler, Lambda,
            API Gateway, DynamoDB · estado en S3 versionado con use_lockfile
```

## 2. Restricciones reales de la cuenta y cómo se resolvieron

| Restricción | Impacto | Solución |
|---|---|---|
| SCP: solo **us-east-2** | ECR/EKS en us-east-1 → *explicit deny* | Todo en Ohio |
| SCP: **iam:*OpenIDConnectProvider** denegado | eksctl, IRSA y OIDC de GitHub fallan | Sin OIDC: autoscaler con permisos en el rol del nodo; GitHub con usuario IAM de permisos mínimos y llaves en *Secrets* |
| **Plan gratuito** (solo instancias *free-tier-eligible*) | c7i.xlarge / c7i.2xlarge no arrancan | Nodos y generador en **c7i-flex.large** |
| Agones 1.60+ no soporta Kubernetes 1.33 | — | **Agones 1.59.0**, autoscaler **v1.33.6** |
| GitHub gratis: *Required reviewers* solo en repos públicos | Sin aprobación manual | Repo público (secrets siguen cifrados) |
| Balanceador clásico de EKS sin UDP | Helm esperaba para siempre al ping UDP de Agones | `agones.ping.udp.expose=false` |
| Sin consola web de la cuenta del proyecto | — | Todo por AWS CLI; capturas de terminal |

## 3. Resultados por práctica

| Práctica | Resultado clave | Evidencia |
|---|---|---|
| 3.1 IA | PPO: 0.5 → 16.9 aciertos/episodio; 2 768 decisiones/s/núcleo; 2 000 bots × 10 Hz → **10 vCPU** | C07–C09 |
| 3.2 CI/CD | build → ECR (SHA) → aprobación → deploy; commit roto (12 jugadores) **bloqueado por pruebas**; rollback con `git revert` | C27–C35 |
| 3.3 Contenedores | Fleet con SDK, Ready en 9 s; Allocated → Shutdown → reposición; pod borrado = partida perdida | C17–C26 |
| 3.4 Escalado/carga | **Bug encontrado por la carga** (`/ready` perdido → Scheduled eterno) corregido vía pipeline; buffer 20 %/30 s → 30 %/5 s (429: 552 → 107); **≈ 50 jugadores por nodo**; reacción del Cluster Autoscaler ≈ 45–60 s; 500 espectadores 0 fallas; 12 GB medidos = 12 GB calculados | C36–C53, `resultados/RESULTADOS-3.4.md` |
| 3.5 Serverless | 49 026 peticiones, 0 fallas, Lambda ≈ 50 ms, concurrencia máx. 100/400, *cold start* 480 ms; USD 8.67/mes vs 15.18 VM | C54–C64, `resultados/RESULTADOS-3.5.md` |
| 3.6 IaC | Plan revisado en PR, apply (74 recursos), idempotencia, drift detectado y corregido, destroy | C65–C79 |

## 4. Costos

**Costo real del laboratorio** (Cost Explorer, uso hasta el 16-nov, cubierto por créditos del plan
gratuito): ≈ **USD 4.60** (EKS 3.97, ELB 0.23, ECS/ECR 0.22, VPC 0.18). Créditos restantes: USD 168.68. (C80)

**Costo por jugador-hora** (precios on-demand us-east-2, aprox.):
`costo/h = 0.10 (plano de control EKS) + nodos × 0.085 (c7i-flex.large)`, capacidad ≈ 50 jugadores/nodo.

| CCU | Nodos | USD/h | USD por jugador-hora |
|---|---|---|---|
| 150 | 3 (mínimo) | 0.36 | 0.0024 |
| 1 000 | 20 | 1.80 | **0.0018** |
| 10 000 | 200 | 17.10 | 0.0017 |

Streaming: el egress domina (20 000 espectadores a 1080p = 54 TB/h ≈ USD 4 315/h) → usar ABR y CDN.

## 5. Recomendaciones
1. FleetAutoscaler **30 %, mínimo 5, sync 5 s** (ya en `k8s/fleetautoscaler-ajustado.yaml`).
2. Mínimo **3 nodos** (≈ 150 jugadores sin esperar al Cluster Autoscaler, que tarda ~1 min).
3. En una cuenta sin plan gratuito: nodos **c7i.xlarge** (≈ 10 partidas/nodo) y generador ≥ 8 vCPU.
4. Reintentar siempre las llamadas al SDK de Agones (`/ready`) y poner *timeouts* explícitos en Helm.
5. Servir el cliente desde un dominio (S3 + CloudFront): `file://` envía `Origin: null` y rompe CORS.
6. Tabla de líderes: reemplazar `Scan` por un índice por puntos o caché del top 10.

## 6. Guion de la demo (10 min)
`terraform apply` (o `terraform output` si ya está) → cliente jugando en la nube → rampa de Locust →
Grafana (CCU / Allocated / nodos subiendo) → Top 10 global actualizándose → `terraform destroy`.
