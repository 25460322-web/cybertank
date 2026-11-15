"""Práctica 3.5 · Tabla de líderes serverless de Cybertank (AWS Lambda + DynamoDB).

POST {"jugador": "ana", "puntos": 100}  → suma puntos y una partida
GET                                     → top 10 global
Funciona detrás de una API Gateway HTTP API (payload 2.0) o una Function URL.
"""
import base64
import json
import os
from decimal import Decimal

import boto3

tabla = boto3.resource("dynamodb").Table(os.environ.get("TABLA", "cybertank-scores"))
CABECERAS = {"Content-Type": "application/json"}


def lambda_handler(event, context):
    metodo = event["requestContext"]["http"]["method"]
    if metodo == "POST":                                   # registrar puntos
        body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body)
        try:
            d = json.loads(body)
            jugador, puntos = str(d["jugador"])[:32], Decimal(int(d["puntos"]))
        except (ValueError, KeyError, TypeError):
            return {"statusCode": 400, "headers": CABECERAS,
                    "body": json.dumps({"error": "se espera {jugador, puntos}"})}
        tabla.update_item(
            Key={"jugador": jugador},
            UpdateExpression="ADD puntos :p, partidas :uno",
            ExpressionAttributeValues={":p": puntos, ":uno": 1})
        return {"statusCode": 201, "headers": CABECERAS, "body": json.dumps({"ok": True})}

    items = tabla.scan(ProjectionExpression="jugador, puntos")["Items"]   # GET: top 10
    top = sorted(items, key=lambda i: i["puntos"], reverse=True)[:10]
    return {"statusCode": 200, "headers": CABECERAS, "body": json.dumps(top, default=int)}
