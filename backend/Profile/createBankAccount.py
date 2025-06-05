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
        saldo = body.get('saldo', "0")  # Tomar el saldo que viene en la solicitud, si no, usar "0"

        # Incluimos el atributo 'saldo' como el valor que se recibe en el cuerpo de la solicitud
        item = {
            "usuario_id": user_id,
            "cuenta_id": cuenta_id,
            "banco": banco,
            "moneda": moneda,
            "numero_cuenta": numero_cuenta,
            "tipo_cuenta": tipo_cuenta,
            "alias": alias,
            "saldo": str(saldo)  # Convertir el saldo a string
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
