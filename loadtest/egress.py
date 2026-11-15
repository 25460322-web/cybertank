"""Práctica 3.4 · Extrapolación del egress del streaming.

GB/hora = CCV × bitrate(kbps) × 3600 / (8 × 10^6)
Precios de CloudFront (EE. UU./Europa, por GB). Verifícalos en calculator.aws.
"""
import sys

TRAMOS = [(10_240, 0.085), (40_960, 0.080), (102_400, 0.060), (358_400, 0.040), (float("inf"), 0.030)]


def gb_por_hora(ccv, kbps):
    return ccv * kbps * 3600 / 8e6


def costo(gb):
    total, restante = 0.0, gb
    for tamano, precio in TRAMOS:
        usado = min(restante, tamano)
        total += usado * precio
        restante -= usado
        if restante <= 0:
            break
    return total


if __name__ == "__main__":
    ccv = int(sys.argv[1]) if len(sys.argv) > 1 else 20_000
    kbps = int(sys.argv[2]) if len(sys.argv) > 2 else 6_000
    horas = float(sys.argv[3]) if len(sys.argv) > 3 else 1
    gb = gb_por_hora(ccv, kbps) * horas
    print(f"{ccv:,} espectadores × {kbps:,} kbps × {horas:g} h = {gb:,.0f} GB ≈ {gb/1000:,.2f} TB")
    print(f"Costo estimado CloudFront: USD {costo(gb):,.0f} (sin contar la capa gratuita de 1 TB/mes)")
