import boto3
import os
import json
from decimal import Decimal
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table_name = os.environ["TABLE_BANKACC"]
table = dynamodb.Table(table_name)

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    try:
        # Validar el token y obtener el ID del usuario
        user_id = validate_token_and_get_user(event)

        # Consultar las cuentas bancarias del usuario
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('usuario_id').eq(user_id)
        )

        # Incluir el saldo en la respuesta
        accounts = response.get("Items", [])
        for account in accounts:
            account['saldo'] = account.get('saldo', 0)

        return {
            "statusCode": 200,
            "body": json.dumps(accounts, default=decimal_default),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
