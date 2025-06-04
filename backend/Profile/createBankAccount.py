import boto3
import os
import json
import uuid
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["TABLE_BANKACC"])

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)
        body = json.loads(event.get('body', '{}'))

        cuenta_id = str(uuid.uuid4())
        banco = body['banco']
        moneda = body['moneda']
        numero_cuenta = body['numero_cuenta']
        tipo_cuenta = body['tipo_cuenta']
        alias = body.get('alias', '')

        # Incluimos el atributo 'saldo' como string, inicializado en "0"
        item = {
            "usuario_id": user_id,
            "cuenta_id": cuenta_id,
            "banco": banco,
            "moneda": moneda,
            "numero_cuenta": numero_cuenta,
            "tipo_cuenta": tipo_cuenta,
            "alias": alias,
            "saldo": "0"  # saldo inicial como string
        }

        # Guardamos la cuenta bancaria en la tabla DynamoDB
        table.put_item(Item=item)

        return {
            'statusCode': 201,
            'body': json.dumps({'message': 'Cuenta registrada con éxito', 'cuenta_id': cuenta_id})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
