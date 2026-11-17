# Cybertank · Guía paso a paso (Unidad 3 en AWS)

**Cybertank** es un juego de guerra de tanques 5 vs 5 que corre en la nube de AWS. Esta guía
sigue las 6 prácticas de la Unidad 3 y el proyecto integrador. Cada vez que veas
**📸 Cxx** toma esa captura y guárdala como `docs/capturas/Cxx-descripcion.png`.
Al final está la **lista maestra de capturas** para que no se te pase ninguna.

> **Orden de trabajo** (el mismo que pide el material): 0 → 3.1 → juego local → 3.3 → 3.2 → 3.4 → 3.5 → 3.6 → integrador.
> En el reporte las presentas por número de tema (3.1 a 3.6).

## Qué hay en el repositorio

| Carpeta | Contenido | Práctica |
|---|---|---|
| `ai/` | `entrenar_bot.py`: bot artillero con aprendizaje por refuerzo (PPO) | 3.1 |
| `server/` | `server.py` (servidor de partida), `test_server.py`, `Dockerfile` | 3.3 |
| `client/` | `index.html`: cliente del juego en el navegador | 3.3 / demo |
| `.github/workflows/` | `deploy.yml`: pipeline CI/CD hacia Amazon ECR y EKS | 3.2 |
| `aws/` | `cluster.yaml` (eksctl), políticas IAM para GitHub | 3.2 / 3.3 |
| `k8s/` | Fleet, FleetAutoscaler, PodMonitor, asignación, tablero de Grafana | 3.3 / 3.4 |
| `loadtest/` | `locustfile.py` (jugadores, espectadores, tabla de líderes), análisis | 3.4 / 3.5 |
| `serverless/` | `lambda_function.py`: tabla de líderes | 3.5 |
| `infra/` | Terraform: VPC, EKS, ECR, Agones, autoscaler, Lambda, DynamoDB, API | 3.6 |

## Reglas para capturas (léelas antes de empezar)

1. **Nunca** captures llaves secretas, contraseñas, el archivo `client.key` ni el contenido de los certificados.
2. **Tapa el número de cuenta de AWS** (12 dígitos) en las capturas; puedes dejar visibles los nombres de recursos.
3. Que se vea la **fecha/hora** (barra de tareas) o el comando completo: el profesor sabe así que la evidencia es tuya y real.
4. En la terminal, captura **el comando y su resultado** en la misma imagen.
5. Con `Win + Shift + S` capturas una zona de la pantalla en Windows.

## Costos en AWS (us-east-2, orientativos)

| Recurso | Precio aprox. | Cuándo existe |
|---|---|---|
| Plano de control EKS | USD 0.10/h | Mientras exista el clúster |
| Nodo c7i.xlarge (4 vCPU) | USD 0.18/h c/u | 3 nodos mínimo → ≈ USD 0.64/h con EKS |
| 10 nodos durante la prueba de carga | ≈ USD 1.9/h | Solo en la práctica 3.4 |
| VM de Locust c7i.2xlarge | ≈ USD 0.36/h | Solo en la práctica 3.4 |
| CloudFront (15 GB de prueba) | gratis (1 TB/mes incluido) | Práctica 3.4 |
| Lambda + DynamoDB + API Gateway | dentro de la capa gratuita | Práctica 3.5 |

> **Regla de oro:** al terminar cada sesión borra el clúster (`eksctl delete cluster` en 3.3–3.5,
> `terraform destroy` en 3.6). Un clúster olvidado un mes cuesta ≈ USD 460.

---

## 0 · Preparación

Todos los comandos están escritos para **Git Bash** (viene con Git para Windows). Abre Git Bash en la carpeta del proyecto.

> **Región: us-east-2 (Ohio).** La cuenta del curso pertenece a la organización AWS de la escuela, y una
> *Service Control Policy* bloquea ECR, EKS, EC2, Lambda, DynamoDB y API Gateway en cualquier otra región.
> Por eso todo el proyecto usa **us-east-2**. En la consola, revisa siempre arriba a la derecha que diga *Ohio*.
> GameLift y SageMaker están bloqueados incluso en Ohio: por eso usamos Agones y Colab.

### 0.1 Cuenta de AWS segura
1. Entra a <https://console.aws.amazon.com> con el usuario que te dio la escuela (`admin-<matrícula>`); ya tiene `AdministratorAccess` y sus llaves de CLI.
2. Activa **MFA** en ese usuario: **IAM → Users → admin-<matrícula> → Security credentials → Assign MFA device**.

📸 **C01** — IAM → Security credentials mostrando MFA activo (tapa el número de cuenta).

### 0.2 Alerta de presupuesto
**Billing and Cost Management → Budgets → Create budget → Monthly cost budget**, monto USD 10, alerta a tu correo al 80 %.

📸 **C02** — El presupuesto creado en la lista de Budgets.

### 0.3 Cuota de vCPU (equivale al límite de 8 vCPU de Google)
Las cuentas nuevas de AWS suelen tener entre 5 y 32 vCPU permitidas. La práctica 3.4 necesita
hasta 12 nodos × 4 vCPU + la VM de Locust (8 vCPU) ≈ 56 vCPU.

**Service Quotas → Amazon EC2 → "Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances" → Request increase** a **64**.
Pídelo el primer día: la aprobación puede tardar de minutos a 2 días.

📸 **C03** — La solicitud de aumento de cuota (estado *Pending* o *Approved*).

Pide también **Service Quotas → AWS Lambda → Concurrent executions** a 1 000 si el valor actual es 10 (lo usarás en 3.5).

### 0.4 Herramientas
En PowerShell (como administrador):
```powershell
winget install Hashicorp.Terraform
winget install Helm.Helm
winget install Gyan.FFmpeg
```
- **eksctl:** descarga `eksctl_Windows_amd64.zip` de <https://github.com/eksctl-io/eksctl/releases>, descomprime `eksctl.exe` en `C:\herramientas` y agrega esa carpeta al PATH.
- **Docker Desktop** ya lo tienes: ábrelo antes de las prácticas.
- Ya tienes AWS CLI, kubectl, Git y Python.

Cierra y abre Git Bash, y configura AWS con la llave del usuario `cybertank-admin`:
```bash
aws configure            # región: us-east-2, formato: json
docker --version; kubectl version --client; helm version; terraform version; eksctl version; aws --version
aws sts get-caller-identity
```
📸 **C04** — Las versiones de todas las herramientas.
📸 **C05** — `aws sts get-caller-identity` (tapa el número de cuenta).

### 0.5 Repositorio en GitHub
Crea un repositorio vacío `cybertank` en GitHub y súbelo:
```bash
git init -b main
git add .
git commit -m "Cybertank: estructura inicial"
git remote add origin https://github.com/<USUARIO>/cybertank.git
git push -u origin main
```
> El primer push dispara el pipeline y **fallará** porque aún no configuras AWS (práctica 3.2). Es normal; ignóralo por ahora.

📸 **C06** — El repositorio en GitHub mostrando las carpetas.

---

## 1 · Práctica 3.1 — Entrenar y servir el bot artillero

El bot aprende a girar la torreta hacia un tanque enemigo que se mueve y a disparar solo cuando está alineado.

1. Abre <https://colab.research.google.com> → *Nuevo notebook*.
2. **Entorno de ejecución → Cambiar tipo de entorno → GPU T4**.
   📸 **C07** — La ventana con GPU T4 seleccionada.
3. Sube `ai/entrenar_bot.py` (icono de carpeta a la izquierda → subir) y ejecuta en una celda:
   ```python
   !pip install -q gymnasium stable-baselines3
   !python entrenar_bot.py --pasos 100000
   ```
   Tarda entre 3 y 8 minutos (entrena dos veces: CPU y GPU).
4. Al final imprime la **TABLA PARA EL ENTREGABLE 3.1**.
   📸 **C08** — La salida completa: "Bot al azar" vs "Bot entrenado", tiempos CPU/GPU y la tabla.
5. Abre <https://calculator.aws> → *Create estimate* → **Amazon EC2** → us-east-2 → instancia `c7i.xlarge` (4 vCPU) y calcula cuántas necesitas para las vCPU que dio la tabla.
   📸 **C09** — La calculadora con el costo por hora.

**Para el reporte:** explica por qué la GPU **no** fue más rápida (red pequeña: copiar datos a la GPU cuesta más que el cálculo) y por qué entrenar en Spot sí es buena idea (se reanuda desde un checkpoint) pero servir partidas no.

---

## 2 · Probar Cybertank en tu PC (antes de la nube)

```bash
cd server
pip install -r requirements.txt pytest
pytest -v
```
📸 **C10** — Las 7 pruebas en verde.

```bash
python server.py
```
Abre `client/index.html` con doble clic **en dos pestañas** del navegador, pon nombres distintos y pulsa *Entrar a la partida*. Mueve con WASD, apunta con el ratón y dispara con clic.

📸 **C11** — Dos tanques en la arena disparándose, con la tabla de la partida a la derecha.

Abre <http://localhost:9100/metrics> y busca `cybertank_`.
📸 **C12** — Las métricas `cybertank_players_connected`, `cybertank_shots_total`, `cybertank_kills_total`.

**Bots de prueba local** (en otra terminal, con el servidor encendido):
```bash
cd loadtest
pip install -r requirements.txt
SERVIDOR_FIJO=localhost:7654 locust -f locustfile.py Jugador -u 8 -r 2 -t 1m --headless
```
Mientras corre, mira el navegador: aparecen 8 tanques "bot-xxxx" moviéndose y disparando.
📸 **C13** — El navegador con tu tanque y los bots.

Detén el servidor con `Ctrl + C`.

---

## 3 · Práctica 3.3 — Contenedores y orquestación (Docker + EKS + Agones)

### Paso 1 · Imagen Docker
Abre Docker Desktop y espera a que diga *Engine running*.
```bash
cd server
docker build -t cybertank-server:1.0 .
docker run --rm -p 7654:7654 -p 9100:9100 cybertank-server:1.0
```
En otra terminal: `curl -s localhost:9100/metrics | grep cybertank`

📸 **C14** — `docker build` terminado y `docker run` mostrando "Cybertank escuchando en :7654".
📸 **C15** — `curl` mostrando las métricas desde el contenedor.

Abre `client/index.html` y juega contra el contenedor (opcional, para comprobar). Detén con `Ctrl + C`.

### Paso 2 · Publicar en Amazon ECR
```bash
export CUENTA=$(aws sts get-caller-identity --query Account --output text)
export REG=$CUENTA.dkr.ecr.us-east-2.amazonaws.com
aws ecr create-repository --repository-name cybertank-server --region us-east-2
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin $REG
docker tag cybertank-server:1.0 $REG/cybertank-server:1.0
docker push $REG/cybertank-server:1.0
```
📸 **C16** — Consola **Amazon ECR → cybertank-server** con la imagen `1.0`.

### Paso 3 · Clúster EKS (15–20 minutos)
```bash
cd ..          # raíz del proyecto
eksctl create cluster -f aws/cluster.yaml
kubectl get nodes -o wide
```
> **Problema encontrado (cuenta de la escuela):** con `withOIDC: true` eksctl falló con
> `AccessDenied ... iam:GetOpenIDConnectProvider ... explicit deny in a service control policy`.
> La organización bloquea los proveedores OIDC de IAM. El plano de control quedó *ACTIVE* pero sin
> complementos ni nodos. **Solución:** `withOIDC: false` (el Cluster Autoscaler y el vpc-cni usan
> los permisos del rol del nodo) y completar lo que faltó:
> ```bash
> for a in vpc-cni kube-proxy coredns; do aws eks create-addon --cluster-name cybertank --addon-name $a; done
> eksctl create nodegroup -f aws/cluster.yaml
> ```
>
> **Segundo problema:** los nodos nunca se unieron. En *EC2 → Auto Scaling groups → Activity* aparecía
> `InvalidParameterCombination - The specified instance type is not eligible for Free Tier`.
> La cuenta está en **plan gratuito** (`aws freetier get-account-plan-state` → `FREE`, con créditos),
> que solo permite tipos *free-tier-eligible*
> (`aws ec2 describe-instance-types --filters Name=free-tier-eligible,Values=true`).
> **Solución:** cambiar a **c7i-flex.large** (2 vCPU, 4 GiB, misma familia c7i), borrar el grupo atorado
> y crearlo de nuevo:
> ```bash
> eksctl delete nodegroup --cluster cybertank --name juego --wait
> eksctl create nodegroup -f aws/cluster.yaml
> ```
📸 **C17** — Final de `eksctl` ("EKS cluster "cybertank" in "us-east-2" region is ready") y `kubectl get nodes` con 3 nodos y su **EXTERNAL-IP**.
📸 **C18** — Consola **EKS → Clusters → cybertank → Compute** con el node group `juego` (mín 3, máx 12).

**Abrir los puertos de las partidas** (7000–8000) a internet:
```bash
SG=$(aws eks describe-cluster --name cybertank --query cluster.resourcesVpcConfig.clusterSecurityGroupId --output text)
aws ec2 authorize-security-group-ingress --group-id $SG --ip-permissions \
  'IpProtocol=tcp,FromPort=7000,ToPort=8000,IpRanges=[{CidrIp=0.0.0.0/0}]' \
  'IpProtocol=udp,FromPort=7000,ToPort=8000,IpRanges=[{CidrIp=0.0.0.0/0}]'
```
📸 **C19** — Consola **EC2 → Security Groups → (el SG del clúster) → Inbound rules** con TCP y UDP 7000-8000.

**Autoescalado de nodos** (en GKE viene integrado; en EKS se instala el Cluster Autoscaler):
```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo add agones https://agones.dev/chart/stable
helm repo update
helm install cluster-autoscaler autoscaler/cluster-autoscaler -n kube-system \
  --set autoDiscovery.clusterName=cybertank --set awsRegion=us-east-2 \
  --set image.tag=v1.33.6        # la versión del autoscaler debe coincidir con la de Kubernetes (1.33)
kubectl get pods -n kube-system | grep autoscaler
```
📸 **C20** — El pod `cluster-autoscaler` en estado `Running`.

### Paso 4 · Agones
```bash
# Agones 1.60+ solo soporta Kubernetes 1.34-1.36; para el clúster 1.33 se fija la 1.59 (soporta 1.33-1.35)
helm install agones agones/agones -n agones-system --create-namespace --version 1.59.0
kubectl get pods -n agones-system
```
📸 **C21** — Los pods de Agones (`agones-controller`, `agones-allocator`, `agones-extensions`, `agones-ping`) en `Running`.

### Paso 5 · Flota de servidores de tanques
Edita `k8s/fleet.yaml`: cambia `<CUENTA>` por tu número de cuenta. Luego:
```bash
kubectl apply -f k8s/fleet.yaml
kubectl get gameservers
```
📸 **C22** — 3 GameServers en estado **Ready** con su ADDRESS y PORT (antes de la asignación).

```bash
kubectl create -f k8s/allocation.yaml
kubectl get gameservers
```
📸 **C23** — Uno de ellos pasó a **Allocated** (después de la asignación).

### Paso 6 · ¡Jugar en la nube!
Toma la ADDRESS y el PORT del servidor **Allocated** y ábrelo en el cliente:
`client/index.html?server=ws://<ADDRESS>:<PORT>&nombre=TuNombre` (o escríbelo en el cuadro del servidor).
Abre otra pestaña (o pásale el enlace a un compañero) para tener un rival.

📸 **C24** — La partida funcionando contra el servidor en AWS (que se vea la IP pública en el cuadro del servidor y el ping).

Cierra las pestañas y vuelve a mirar:
```bash
kubectl get gameservers -w
```
📸 **C25** — El servidor que usaste pasa a `Shutdown` y la flota crea uno nuevo en `Ready` (la partida terminó: el servidor llamó a `/shutdown`).

### Paso 7 · Pregunta del entregable: ¿y si borro un pod Allocated?
```bash
kubectl create -f k8s/allocation.yaml
kubectl get gameservers                          # anota el NAME del Allocated
kubectl delete pod <NAME-del-Allocated>
kubectl get gameservers -w
```
📸 **C26** — El pod borrado y la flota reponiendo un servidor Ready.

**Para el reporte:** la partida que vivía en ese pod **se pierde** (el estado está en memoria); Agones repone la cantidad de servidores pero no la partida. Por eso Kubernetes nunca debe apagar un servidor Allocated (Agones lo protege del autoscaler y de los updates).

> **Fin de sesión:** si no vas a seguir hoy, `eksctl delete cluster -f aws/cluster.yaml` (y al volver repite los pasos 3 a 5).

---

## 4 · Práctica 3.2 — Pipeline CI/CD con GitHub Actions → ECR → EKS

Lo recomendado en producción es **OIDC** (GitHub obtiene credenciales temporales sin llaves guardadas).
> **En la cuenta de la escuela no se puede:** la SCP niega `iam:CreateOpenIDConnectProvider` (el mismo bloqueo de la 3.3).
> Alternativa usada: un **usuario IAM `github-deployer` con permisos mínimos** cuyas llaves se guardan como
> **secrets cifrados** de GitHub (nunca en el código). Riesgo: son llaves de larga duración → rotarlas
> (`aws iam create-access-key` / `delete-access-key`) y borrarlas al terminar el curso.

### Paso 1 · Usuario IAM con permisos mínimos
Edita `aws/github-deployer-policy.json` (pon `<CUENTA>`): solo permite subir a ECR `cybertank-server` y `eks:DescribeCluster`.
```bash
aws iam create-user --user-name github-deployer
aws iam put-user-policy --user-name github-deployer --policy-name cybertank-deploy   --policy-document file://aws/github-deployer-policy.json
```
📸 **C27** — `aws iam get-user-policy --user-name github-deployer --policy-name cybertank-deploy` (los 3 permisos).

### Paso 2 · Dejar que el usuario actualice la flota en EKS
```bash
export CUENTA=$(aws sts get-caller-identity --query Account --output text)
U=arn:aws:iam::$CUENTA:user/github-deployer
aws eks create-access-entry --cluster-name cybertank --principal-arn $U
aws eks associate-access-policy --cluster-name cybertank --principal-arn $U   --policy-arn arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy   --access-scope type=cluster
```
📸 **C28** — `aws eks list-access-entries` / `list-associated-access-policies` con `github-deployer`.

### Paso 3 · Secrets, variable y aprobación en GitHub
Las llaves pasan directo de AWS a GitHub **sin mostrarse en pantalla**:
```bash
K=$(aws iam create-access-key --user-name github-deployer      --query "AccessKey.[AccessKeyId,SecretAccessKey]" --output text)
printf '%s' "$(echo "$K" | cut -f1)" | gh secret set AWS_ACCESS_KEY_ID
printf '%s' "$(echo "$K" | cut -f2)" | gh secret set AWS_SECRET_ACCESS_KEY
unset K
gh variable set EKS_CLUSTER --body cybertank
```
**Aprobación manual:** *Settings → Environments → produccion → Required reviewers* → agrégate.
> En GitHub gratuito los *Required reviewers* solo funcionan en repos **públicos** (privados requieren Pro);
> por eso el repo se hizo público. Los secrets siguen cifrados y no se ven.

📸 **C29** — *Settings → Secrets and variables → Actions*: los 2 secrets (valores ocultos) y la variable `EKS_CLUSTER`.
📸 **C30** — El environment `produccion` con *Required reviewers*.

### Paso 4 · Primer pipeline en verde
Sube el `fleet.yaml` con tu cuenta y dispara el pipeline:
```bash
git add . && git commit -m "CI/CD: despliegue a EKS" && git push
```
En **Actions** aprueba el job `deploy` cuando lo pida. Mientras corre:
```bash
kubectl get gameservers -w
```
📸 **C31** — El workflow con los jobs `build` y `deploy` en verde.
📸 **C32** — El paso *Construir y publicar imagen* con la etiqueta del commit (SHA).
📸 **C33** — **ECR → cybertank-server** mostrando la imagen con la etiqueta SHA además de `1.0`.
📸 **C34** — `kubectl get gameservers -w` mostrando cómo se reemplazan los servidores Ready (los Allocated se drenan).

### Paso 5 · Demostrar que CI protege producción
Cambia en `server/server.py` `MAX_JUGADORES = 10` por `12`, haz commit y push.
📸 **C35** — El pipeline en **rojo** en el paso *Pruebas*, y **sin** imagen nueva en ECR.

Revierte el cambio (`git revert HEAD && git push`) para volver a verde.

**Para el reporte (rollback):** cada versión es una imagen inmutable con el SHA del commit. Para volver atrás:
`git revert` del commit malo (el pipeline publica y despliega de nuevo), o de inmediato
`kubectl set image`/editar `fleet.yaml` con la etiqueta SHA anterior y `kubectl apply -f k8s/fleet.yaml`; Agones reemplaza los servidores libres y drena los ocupados.

---

## 5 · Práctica 3.4 — Autoescalado, métricas y simulación de clientes

### Paso 1 · Autoescalado de la flota
```bash
kubectl apply -f k8s/fleetautoscaler.yaml
kubectl get fleetautoscaler
```
📸 **C36** — El FleetAutoscaler creado (buffer 20 %, mín 3, máx 200).

### Paso 2 · Prometheus y Grafana
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts && helm repo update
helm install monitoreo prometheus-community/kube-prometheus-stack -n monitoring --create-namespace \
  --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false
helm upgrade agones agones/agones -n agones-system --reuse-values \
  --set agones.metrics.serviceMonitor.enabled=true
kubectl apply -f k8s/podmonitor.yaml
kubectl get pods -n monitoring
kubectl get secret -n monitoring monitoreo-grafana -o jsonpath="{.data.admin-password}" | base64 -d; echo
kubectl port-forward -n monitoring svc/monitoreo-grafana 3000:80
```
Entra a <http://localhost:3000> (usuario `admin`, la contraseña del comando anterior; **no la captures**).
**Dashboards → New → Import → Upload JSON** → `k8s/grafana-dashboard.json`.

📸 **C37** — Pods de `monitoring` en Running.
📸 **C38** — El tablero "Cybertank · Jugadores y flota" con datos (antes de la carga).

Deja el `port-forward` abierto en esa terminal.

### Paso 3 · Bitácora del escalado (tiempo de reacción)
En otra terminal de Git Bash, deja corriendo durante las pruebas:
```bash
while true; do
  echo "$(date +%T) $(kubectl get fleet cybertank-fleet --no-headers | awk '{print "deseados="$3" actuales="$4" asignados="$5" listos="$6}') nodos=$(kubectl get nodes --no-headers | wc -l)"
  sleep 10
done | tee escalado.log
```
Con `escalado.log` calculas cuántos segundos pasan entre que sube la carga y llegan nodos nuevos.

### Paso 4 · Stream de prueba (S3 + CloudFront)
```bash
mkdir stream && cd stream
ffmpeg -f lavfi -i testsrc2=size=640x360:rate=30 -t 300 \
  -c:v libx264 -preset veryfast -b:v 800k -maxrate 800k -bufsize 1600k -g 60 \
  -hls_time 2 -hls_playlist_type vod -hls_segment_filename "360p_%03d.ts" 360p.m3u8
aws s3 mb s3://cybertank-stream-<TU-ID> --region us-east-2
aws s3 cp . s3://cybertank-stream-<TU-ID>/live/cybertank/ --recursive
cd ..
```
En la consola: **CloudFront → Create distribution** → *Origin*: tu bucket `cybertank-stream-<TU-ID>` → *Origin access*: **Origin access control (recommended)** → crea la distribución y acepta **actualizar la política del bucket** cuando lo ofrezca. Si el asistente pide elegir plan, elige el de pago por uso o el gratuito. Espera a que diga *Deployed* y copia su dominio `dxxxx.cloudfront.net`.

```bash
curl -s https://dxxxx.cloudfront.net/live/cybertank/360p.m3u8 | head
```
📸 **C39** — S3 con los segmentos `.ts` y el `.m3u8`.
📸 **C40** — CloudFront con la distribución *Deployed* y el `curl` devolviendo el manifiesto.

### Paso 5 · VM generadora de carga (Locust)
**EC2 → Launch instance**: nombre `locust-gen`, **Ubuntu 24.04**, tipo **c7i.2xlarge** (8 vCPU), región us-east-2, *Create new key pair* `cybertank-locust` (.pem, guárdalo en la carpeta del proyecto: el `.gitignore` lo excluye), *Allow SSH from My IP*.

📸 **C41** — La instancia `locust-gen` en *Running* (tipo c7i.2xlarge).

Certificados del allocator de Agones y su dirección (desde tu PC, en la raíz del proyecto):
```bash
kubectl get secret allocator-client.default -n default -o jsonpath="{.data.tls\.crt}" | base64 -d > client.crt
kubectl get secret allocator-client.default -n default -o jsonpath="{.data.tls\.key}" | base64 -d > client.key
kubectl get secret allocator-tls-ca -n agones-system -o jsonpath="{.data.tls-ca\.crt}" | base64 -d > ca.crt
kubectl get svc agones-allocator -n agones-system -o jsonpath="{.status.loadBalancer.ingress[0].hostname}"; echo
```
(En AWS el allocator queda detrás de un balanceador con **nombre DNS** en lugar de IP; el `locustfile.py` ya desactiva la verificación TLS para el laboratorio. En producción se regenera el certificado con ese nombre.)

```bash
chmod 400 cybertank-locust.pem
VM=<IP-pública-de-locust-gen>
scp -i cybertank-locust.pem client.crt client.key ca.crt loadtest/locustfile.py loadtest/requirements.txt loadtest/analizar.py loadtest/egress.py ubuntu@$VM:~
ssh -i cybertank-locust.pem ubuntu@$VM
# --- dentro de la VM ---
sudo apt-get update && sudo apt-get install -y python3-pip
pip install -r requirements.txt --break-system-packages
export PATH=$PATH:~/.local/bin
export ALLOCATOR_HOST=<hostname-del-allocator>
locust --version
```
📸 **C42** — La sesión SSH en la VM con `locust --version` (no muestres los certificados).

### Paso 6 · Escenarios de carga
Dentro de la VM:
```bash
# Rampa: 1 000 jugadores, 2 nuevos por segundo, 20 min
locust -f locustfile.py Jugador -u 1000 -r 2 -t 20m --headless --processes -1 --csv rampa
```
Durante la rampa:
📸 **C43** — Grafana a mitad de la rampa: CCU subiendo, Allocated subiendo, Ready ≈ 20 %, nodos aumentando.
📸 **C44** — `kubectl get nodes` mostrando nodos nuevos creados por el Cluster Autoscaler (y `escalado.log`).
📸 **C45** — Consola **EC2 → Auto Scaling Groups** (el del node group) con *Desired capacity* aumentada y su *Activity history*.
📸 **C46** — Resumen final de Locust de la rampa (tabla con `asignacion`, `conexion`, `rtt`).

> **Truco para la demo:** durante la rampa abre `client/index.html` contra un servidor Allocated
> (dirección de `kubectl get gameservers`) y verás a los bots de carga jugando. 📸 **C47**

Espera a que la flota baje (≈ 10 min, verás nodos eliminados en `escalado.log`) y lanza el pico:
```bash
# Pico: los mismos 1 000 jugadores entrando en 20 s
locust -f locustfile.py Jugador -u 1000 -r 50 -t 10m --headless --processes -1 --csv pico
```
📸 **C48** — Grafana durante el pico (se ve el salto y cuánto tarda la flota en alcanzarlo).
📸 **C49** — Resumen final de Locust del pico (errores de `asignacion`/`conexion` si el escalado no alcanzó).

```bash
# Espectadores: 500 a 360p durante 5 min contra CloudFront
locust -f locustfile.py Espectador --host https://dxxxx.cloudfront.net -u 500 -r 50 -t 5m \
  --headless --processes -1 --csv stream
```
📸 **C50** — Resumen de Locust del stream (`manifiesto`, `segmento`, fallas por *rebuffering*).
📸 **C51** — **CloudFront → Monitoring** (Requests y Bytes downloaded durante la prueba).

### Paso 7 · Análisis
En la VM:
```bash
python3 analizar.py rampa
python3 analizar.py pico
python3 egress.py 500 800 0.0833       # lo que transferiste (5 min)
python3 egress.py 20000 6000 1         # extrapolación: 20 000 espectadores a 1080p, 1 hora
exit
```
Trae los resultados a tu PC:
```bash
mkdir -p resultados && scp -i cybertank-locust.pem "ubuntu@$VM:~/*.csv" "ubuntu@$VM:~/*.png" resultados/
```
📸 **C52** — La gráfica `rampa_ccu_vs_p95.png` (curva CCU vs latencia p95 con la línea de 80 ms).
📸 **C53** — La salida de `egress.py` con la extrapolación a 20 000 espectadores (≈ 54 TB y su costo).

**Para el reporte (entregable 3.4):**
- Capacidad máxima = jugadores donde la p95 cruza 80 ms ÷ nodos activos en ese momento (de `escalado.log`).
- Tiempo de reacción = hora en que se agotaron los Ready − hora en que llegó el nodo nuevo (de `escalado.log`).
- Recomendación justificada: `bufferSize`, tipo de máquina, mínimo de nodos.

### Paso 8 · Limpieza de la sesión
**EC2 → locust-gen → Instance state → Terminate** (o *Stop* si la usarás en 3.5). Borra `client.key` de tu PC al terminar el proyecto.

---

## 6 · Práctica 3.5 — Tabla de líderes serverless (Lambda + DynamoDB + API Gateway)

### Paso 1 · Tabla DynamoDB
**DynamoDB → Create table**: nombre `cybertank-scores`, partition key `jugador` (String), *On-demand*.
📸 **C54** — La tabla creada.

### Paso 2 · Función Lambda
**Lambda → Create function**: `cybertank-leaderboard`, runtime **Python 3.12**. Pega el contenido de `serverless/lambda_function.py` y pulsa **Deploy**.
- *Configuration → Environment variables*: `TABLA` = `cybertank-scores`.
- *Configuration → Permissions →* clic en el rol → *Add permissions → Create inline policy* → JSON:
```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["dynamodb:UpdateItem","dynamodb:Scan"],"Resource":"arn:aws:dynamodb:us-east-2:<CUENTA>:table/cybertank-scores"}]}
```
- *Add trigger → API Gateway → Create a new API → HTTP API → Security: Open*.

📸 **C55** — El código desplegado en Lambda.
📸 **C56** — La política inline del rol (UpdateItem y Scan).
📸 **C57** — El trigger de API Gateway con su *API endpoint*.

### Paso 3 · Probar
```bash
URL=<API endpoint del trigger>
curl -X POST $URL -H "Content-Type: application/json" -d '{"jugador":"ana","puntos":1250}'
curl -X POST $URL -H "Content-Type: application/json" -d '{"jugador":"beto","puntos":800}'
curl $URL
```
📸 **C58** — Los `curl` devolviendo `{"ok": true}` y el top 10 en JSON.
📸 **C59** — DynamoDB → *Explore items* con los jugadores, puntos y partidas.

### Paso 4 · Conectar el juego con la tabla de líderes
En `k8s/fleet.yaml` pon el endpoint en `LEADERBOARD_URL` y aplica (o haz push y que lo aplique el pipeline):
```bash
kubectl apply -f k8s/fleet.yaml
kubectl create -f k8s/allocation.yaml && kubectl get gameservers
```
Abre `client/index.html?server=ws://<ADDRESS>:<PORT>&nombre=TuNombre&lb=<URL>` en dos pestañas y destrúyanse un par de tanques.
📸 **C60** — El juego con el **Top 10 global** a la derecha mostrando tus puntos (cada derribo suma 100).

### Paso 5 · Prueba de carga y arranque en frío
Espera 15 minutos sin usar la función (para forzar el *cold start*). Desde la VM de Locust (o tu PC):
```bash
locust -f locustfile.py Lider --host <URL> -u 500 -r 50 -t 5m --headless --csv lider
```
📸 **C61** — Resumen de Locust (GET top10 y POST puntos, con p99).
📸 **C62** — **Lambda → Monitor**: *Concurrent executions*, *Duration* e *Invocations* durante la prueba.
📸 **C63** — **CloudWatch → Logs** de la función mostrando una línea `REPORT ... Init Duration` (eso es el arranque en frío).

Si ves errores 429/503, tu cuenta tiene límite de concurrencia de Lambda bajo (ver 0.3): documéntalo como hallazgo.

### Paso 6 · Costo serverless vs VM
En <https://calculator.aws>: Lambda con 5 000 000 peticiones/mes, 50 ms, 256 MB vs **EC2 t3.small** encendida 730 h.
📸 **C64** — Las dos estimaciones lado a lado.

### Paso 7 · Fin de la sesión
```bash
eksctl delete cluster -f aws/cluster.yaml
```
📸 **C65** — `eksctl delete cluster` terminado. (En 3.6 todo se vuelve a crear con Terraform.)

---

## 7 · Práctica 3.6 — Toda la plataforma con Terraform

Terraform crea: VPC, EKS + node group autoescalable, reglas de firewall, ECR, Agones,
Cluster Autoscaler, DynamoDB, Lambda y API Gateway. El nombre lleva el *workspace*: `cybertank-default`.

### Paso 1 · Estado remoto
```bash
aws s3 mb s3://cybertank-tfstate-<TU-ID> --region us-east-2
aws s3api put-bucket-versioning --bucket cybertank-tfstate-<TU-ID> --versioning-configuration Status=Enabled
```
Cambia `<TU-ID>` en `infra/main.tf` (bloque `backend "s3"`).
📸 **C66** — El bucket del estado con *Versioning: Enabled*.

### Paso 2 · Init, importar y plan
```bash
export CUENTA=$(aws sts get-caller-identity --query Account --output text)
cd infra
terraform init
terraform fmt && terraform validate
# El repositorio ECR ya existe desde 3.3: se importa en lugar de recrearlo
terraform import aws_ecr_repository.servidor cybertank-server
terraform plan -var rol_github_arn=arn:aws:iam::$CUENTA:role/github-deployer -out plan.tfplan
```
📸 **C67** — `terraform init` exitoso (proveedores aws, helm, archive y módulos descargados).
📸 **C68** — `terraform validate`: *Success! The configuration is valid.*
📸 **C69** — `terraform import` exitoso (concepto: traer recursos existentes al estado).
📸 **C70** — El final de `terraform plan`: *Plan: N to add, 0 to change, 0 to destroy.*

### Paso 3 · Revisión en Pull Request
```bash
git checkout -b infra-terraform
terraform show -no-color plan.tfplan > plan.txt      # .gitignore lo excluye del commit
git add -A && git commit -m "Infraestructura de Cybertank con Terraform" && git push -u origin infra-terraform
```
En GitHub crea el **Pull Request** y pega `plan.txt` (o un resumen) en un comentario. Revísalo y haz *Merge*.
📸 **C71** — El Pull Request con el plan revisado.

### Paso 4 · Apply (≈ 20 minutos)
```bash
terraform apply plan.tfplan
terraform output
```
📸 **C72** — *Apply complete! Resources: N added* y los `outputs` (cluster, registro, leaderboard_url).

### Paso 5 · Usar el clúster creado con código
```bash
aws eks update-kubeconfig --name cybertank-default --region us-east-2
kubectl get nodes
kubectl get pods -n agones-system
kubectl get pods -n kube-system | grep autoscaler
cd ..
kubectl apply -f k8s/fleet.yaml -f k8s/fleetautoscaler.yaml
kubectl get gameservers
```
Actualiza en GitHub la variable `EKS_CLUSTER` = `cybertank-default` y en `fleet.yaml` la `LEADERBOARD_URL` con el output `leaderboard_url`.

📸 **C73** — Nodos, Agones y autoscaler funcionando en el clúster creado por Terraform.
📸 **C74** — Una partida jugándose en este clúster (cliente + `kubectl get gameservers`).

### Paso 6 · Idempotencia y drift
```bash
cd infra
terraform plan -var rol_github_arn=arn:aws:iam::$CUENTA:role/github-deployer
```
📸 **C75** — *No changes. Your infrastructure matches the configuration.* (idempotencia)

Ahora cambia algo **a mano** en la consola: **Lambda → cybertank-default-leaderboard → Configuration → General → Memory** de 256 a 512 MB. Repite el `plan`.
📸 **C76** — `terraform plan` detectando el **drift** (`memory_size: 512 -> 256`).

Corrígelo con `terraform apply -var rol_github_arn=...` para volver al código.

### Paso 7 · Destroy sin recursos huérfanos
El balanceador del allocator lo crea Kubernetes (no Terraform); bórralo primero:
```bash
terraform destroy -target=helm_release.agones -var rol_github_arn=arn:aws:iam::$CUENTA:role/github-deployer
# espera 2 minutos a que AWS elimine el balanceador
terraform destroy -var rol_github_arn=arn:aws:iam::$CUENTA:role/github-deployer
```
📸 **C77** — *Destroy complete! Resources: N destroyed.*

Verifica que no quedó nada cobrando:
- **EC2 → Instances** (sin instancias, salvo locust-gen si la conservas), **Load Balancers** (vacío), **Volumes** (vacío), **Elastic IPs** (vacío).
- **EKS → Clusters** vacío.
- **Resource Groups & Tag Editor → Tag Editor** → *All regions*, tag `Proyecto = cybertank` → sin resultados.

📸 **C78** — Tag Editor sin recursos con `Proyecto = cybertank`.
📸 **C79** — EC2 → Load Balancers vacío.
📸 **C80** — **Billing → Bills** del mes (costo total del laboratorio, sirve para el análisis de costos).

**Variante opcional (entornos):** `terraform workspace new prod` y el mismo código crea `cybertank-prod`.

---

## 8 · Proyecto integrador: día de lanzamiento

Para la demostración en vivo y el reporte, recrea con `terraform apply`, despliega por pipeline y ejecuta la rampa.

**Checklist de entregables ↔ rúbrica**

| Entregable | Evidencia (capturas) | Criterio (peso) |
|---|---|---|
| `infra/` con estado remoto y workspaces | C66–C79 | IaC (20 %) |
| Imagen, Fleet de Agones, SDK integrado, requests/limits | C14–C26, C73 | Contenedores (20 %) |
| Flota, pods y nodos escalan + tiempo medido | C36, C43–C45, C48, `escalado.log` | Autoescalado (20 %) |
| Jugadores y espectadores simulados, curva CCU vs p95 | C46–C53 | Métricas y carga (20 %) |
| Pipeline automático + tabla de líderes bajo carga | C31–C35, C58–C63 | CI/CD y serverless (10 %) |
| Reporte con costo por hora y por jugador | C09, C53, C64, C80 | Comunicación (10 %) |

**Costo por jugador (fórmula para el reporte):**
`costo/h = USD 0.10 (EKS) + nodos × USD 0.18`, y `costo por jugador-hora = costo/h ÷ CCU soportado`.
Ejemplo: 10 nodos con 1 000 jugadores → (0.10 + 1.80) ÷ 1 000 ≈ USD 0.0019 por jugador-hora.

**Estructura sugerida del reporte (máx. 6 páginas):** 1) Arquitectura (diagrama AWS), 2) Bot de IA y dimensionamiento (3.1),
3) Pipeline (3.2), 4) Contenedores y Agones (3.3), 5) Resultados de carga y escalado (3.4), 6) Serverless (3.5),
7) IaC (3.6), 8) Costos y recomendaciones.

**Guion de la demo (10 min):** `terraform output` → cliente jugando en la nube → lanzar la rampa → Grafana mostrando
CCU/Allocated/nodos subiendo → top 10 global actualizándose → `terraform destroy`.

---

## Lista maestra de capturas

| # | Qué capturar | Dónde |
|---|---|---|
| C01 | MFA activo | IAM → Security credentials |
| C02 | Presupuesto USD 10 | Billing → Budgets |
| C03 | Aumento de cuota de vCPU | Service Quotas → EC2 |
| C04 | Versiones de las herramientas | Git Bash |
| C05 | `aws sts get-caller-identity` | Git Bash |
| C06 | Repositorio con carpetas | GitHub |
| C07 | GPU T4 seleccionada | Colab |
| C08 | Salida del entrenamiento y tabla 3.1 | Colab |
| C09 | Costo de vCPU para los bots | calculator.aws |
| C10 | `pytest` en verde | Git Bash |
| C11 | Dos tanques jugando en local | Navegador |
| C12 | Métricas `cybertank_*` | localhost:9100/metrics |
| C13 | Bots de Locust jugando en local | Navegador |
| C14 | `docker build` y `docker run` | Git Bash |
| C15 | Métricas desde el contenedor | Git Bash |
| C16 | Imagen 1.0 en ECR | Consola ECR |
| C17 | Clúster listo y 3 nodos con IP externa | Git Bash |
| C18 | Node group 3–12 | Consola EKS |
| C19 | Reglas TCP/UDP 7000-8000 | Consola EC2 → SG |
| C20 | Pod cluster-autoscaler | Git Bash |
| C21 | Pods de Agones | Git Bash |
| C22 | 3 GameServers Ready | Git Bash |
| C23 | Un GameServer Allocated | Git Bash |
| C24 | Partida jugándose en AWS | Navegador |
| C25 | Servidor a Shutdown y reposición | Git Bash |
| C26 | Borrado de un pod Allocated | Git Bash |
| C27 | Usuario github-deployer y su política | Git Bash |
| C28 | Access entry en EKS | Git Bash |
| C29 | Variables del repositorio | GitHub |
| C30 | Environment con aprobación | GitHub |
| C31 | Pipeline en verde | GitHub Actions |
| C32 | Imagen con etiqueta SHA en el log | GitHub Actions |
| C33 | Imagen SHA en ECR | Consola ECR |
| C34 | Reemplazo de GameServers | Git Bash |
| C35 | Pipeline en rojo sin imagen | GitHub Actions |
| C36 | FleetAutoscaler | Git Bash |
| C37 | Pods de monitoring | Git Bash |
| C38 | Tablero Grafana sin carga | Grafana |
| C39 | Segmentos HLS en S3 | Consola S3 |
| C40 | CloudFront Deployed + curl | Consola / Git Bash |
| C41 | VM locust-gen | Consola EC2 |
| C42 | SSH + versión de Locust | Git Bash |
| C43 | Grafana durante la rampa | Grafana |
| C44 | Nodos nuevos + escalado.log | Git Bash |
| C45 | Auto Scaling Group del node group | Consola EC2 |
| C46 | Resumen Locust rampa | VM |
| C47 | Bots de carga jugando en la nube | Navegador |
| C48 | Grafana durante el pico | Grafana |
| C49 | Resumen Locust pico | VM |
| C50 | Resumen Locust stream | VM |
| C51 | Monitoreo de CloudFront | Consola CloudFront |
| C52 | Gráfica CCU vs p95 | Imagen generada |
| C53 | Extrapolación de egress | VM |
| C54 | Tabla DynamoDB | Consola DynamoDB |
| C55 | Código en Lambda | Consola Lambda |
| C56 | Política inline del rol | Consola IAM |
| C57 | Trigger API Gateway | Consola Lambda |
| C58 | `curl` POST y GET | Git Bash |
| C59 | Items en DynamoDB | Consola DynamoDB |
| C60 | Top 10 global en el juego | Navegador |
| C61 | Resumen Locust de la tabla de líderes | VM / Git Bash |
| C62 | Métricas de concurrencia de Lambda | Consola Lambda |
| C63 | Log con Init Duration (cold start) | CloudWatch Logs |
| C64 | Costo Lambda vs EC2 | calculator.aws |
| C65 | Borrado del clúster manual | Git Bash |
| C66 | Bucket del estado con versioning | Consola S3 |
| C67 | `terraform init` | Git Bash |
| C68 | `terraform validate` | Git Bash |
| C69 | `terraform import` | Git Bash |
| C70 | `terraform plan` | Git Bash |
| C71 | Pull Request con el plan | GitHub |
| C72 | `terraform apply` + outputs | Git Bash |
| C73 | Clúster de Terraform funcionando | Git Bash |
| C74 | Partida en el clúster de Terraform | Navegador + Git Bash |
| C75 | Plan sin cambios (idempotencia) | Git Bash |
| C76 | Plan detectando drift | Git Bash |
| C77 | `terraform destroy` completo | Git Bash |
| C78 | Tag Editor sin recursos | Consola |
| C79 | Load Balancers vacío | Consola EC2 |
| C80 | Factura del mes | Billing |

## Problemas comunes

| Síntoma | Causa y solución |
|---|---|
| `eksctl` falla con *VcpuLimitExceeded* o los nodos no crecen | Cuota de vCPU baja: paso 0.3. |
| GameServers se quedan en `Scheduled` | El contenedor no llamó a `/ready`: revisa `kubectl logs <pod> -c cybertank`. |
| El cliente no conecta a `ws://IP:PUERTO` | Falta la regla 7000-8000 en el security group (C19) o el servidor ya pasó a Shutdown. |
| `ImagePullBackOff` | `<CUENTA>` sin reemplazar en `fleet.yaml` o la imagen no está en ECR. |
| Locust: errores SSL en `asignacion` | Usa `ALLOCATOR_HOST` (hostname, sin `https://`); la verificación ya está desactivada. |
| Pipeline: *Not authorized to perform sts:AssumeRoleWithWebIdentity* | El `sub` de `github-oidc-trust.json` no coincide con `repo:USUARIO/REPO:*`. |
| Pipeline `deploy`: *Unauthorized* en kubectl | Falta el access entry del rol (paso 4.2) o `rol_github_arn` en Terraform. |
| `terraform destroy` se atasca en la VPC | Quedó el balanceador del allocator: bórralo en EC2 → Load Balancers y repite. |
| Agones no instala: versión de Kubernetes no soportada | Cambia `version` en `aws/cluster.yaml` / `version_k8s` en Terraform a una que liste agones.dev. |
