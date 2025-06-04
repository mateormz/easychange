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
        moneda = event['pathParameters']['moneda']

        response = table.query(
            IndexName='moneda-index',
            KeyConditionExpression=Key('moneda').eq(moneda)
        )

        cuentas_filtradas = [item for item in response.get("Items", []) if item.get("usuario_id") == user_id]

        # Asegúrate de que 'saldo' sea tratado como un string
        for account in cuentas_filtradas:
            # Si el saldo no existe o es nulo, lo asignamos como "0" (string)
            account['saldo'] = str(account.get('saldo', "0"))

        return {
            "statusCode": 200,
            "body": json.dumps(cuentas_filtradas),  # Ya no necesitamos el 'decimal_default' porque estamos usando strings
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
