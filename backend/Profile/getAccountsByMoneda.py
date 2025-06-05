import boto3
import os
import json
from boto3.dynamodb.conditions import Key
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["TABLE_BANKACC"])


def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        # Verificar si el parámetro 'moneda' está presente en la URL
        if 'moneda' not in event['pathParameters']:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "El parámetro 'moneda' es obligatorio"})
            }

        moneda = event['pathParameters']['moneda']

        response = table.query(
            IndexName='moneda-index',
            KeyConditionExpression=Key('moneda').eq(moneda)
        )

        # Filtrar resultados que pertenezcan al usuario autenticado
        cuentas_filtradas = [item for item in response.get("Items", []) if item.get("usuario_id") == user_id]

        return {
            "statusCode": 200,
            "body": json.dumps(cuentas_filtradas)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
