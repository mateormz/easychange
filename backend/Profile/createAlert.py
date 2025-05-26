import boto3
import os
import json
import uuid
from decimal import Decimal
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_ALERTS'])

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)
        body = json.loads(event.get('body', '{}'))

        alerta_id = str(uuid.uuid4())
        tipo_cambio = body['tipo_cambio']
        umbral = body['umbral']
        direccion = body['direccion']

        item = {
            "usuario_id": user_id,
            "alerta_id": alerta_id,
            "tipo_cambio": tipo_cambio,
	    "umbral": Decimal(str(umbral)),
            "direccion": direccion
        }

        table.put_item(Item=item)

        return {
            "statusCode": 201,
            "body": json.dumps({"message": "Alerta creada", "alerta_id": alerta_id})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
