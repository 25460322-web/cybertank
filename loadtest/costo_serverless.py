"""Práctica 3.5 | Paso 6: costo mensual de la tabla de líderes, serverless vs VM.

Precios on-demand de us-east-2 (Ohio); verifícalos en https://calculator.aws.
Uso: python costo_serverless.py [peticiones_mes] [duracion_ms] [memoria_mb]
"""
import sys

PET = int(sys.argv[1]) if len(sys.argv) > 1 else 5_000_000
MS = float(sys.argv[2]) if len(sys.argv) > 2 else 50
MB = int(sys.argv[3]) if len(sys.argv) > 3 else 256

LAMBDA_PET = 0.20 / 1e6          # USD por petición
LAMBDA_GBS = 0.0000166667        # USD por GB-segundo (x86)
APIGW_HTTP = 1.00 / 1e6          # USD por petición (HTTP API, primeros 300 M)
DDB_ESCR, DDB_LECT = 0.625 / 1e6, 0.125 / 1e6   # on-demand por unidad (feb-2026)
T3_SMALL_H = 0.0208              # USD por hora (Linux, on-demand)
HORAS = 730

gbs = PET * MS / 1000 * MB / 1024
lam = PET * LAMBDA_PET + gbs * LAMBDA_GBS
api = PET * APIGW_HTTP
ddb = PET * 0.2 * DDB_ESCR + PET * 0.8 * DDB_LECT * 2   # 20 % POST, 80 % GET (Scan ~2 RRU)
total_sl = lam + api + ddb
vm = T3_SMALL_H * HORAS

print(f"Carga: {PET:,} peticiones/mes | {MS:.0f} ms | {MB} MB   (80 % GET top10 / 20 % POST)\n")
print(f"{'SERVERLESS':<34}{'USD/mes':>10}")
print(f"  {f'Lambda ({gbs:,.0f} GB-s + peticiones)':<32}{lam:>9.2f}")
print(f"  {'API Gateway HTTP API':<32}{api:>9.2f}")
print(f"  {'DynamoDB on-demand':<32}{ddb:>9.2f}")
print(f"  {'TOTAL':<32}{total_sl:>9.2f}")
print(f"  (capa gratuita: 1 M peticiones y 400 000 GB-s de Lambda al mes => {max(total_sl - 0.20 - min(gbs, 400000) * LAMBDA_GBS, 0):.2f})\n")
print(f"{'VM EC2 t3.small 24x7 (730 h)':<34}{vm:>9.2f}")
print(f"  + no escala sola, hay que parcharla y paga aunque nadie juegue\n")
cruce = vm / (total_sl / PET)
print(f"Punto de equilibrio: serverless es más barato hasta ~ {cruce / 1e6:,.0f} M peticiones/mes")
