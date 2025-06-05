import boto3
import os
import json
from boto3.dynamodb.conditions import Key
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table_name = os.environ["TABLE_BANKACC"]
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    try:
        # Validar token y obtener el ID del usuario
        user_id = validate_token_and_get_user(event)

        # Consultar las cuentas bancarias del usuario
        response = table.query(
            KeyConditionExpression=Key('usuario_id').eq(user_id)
        )

        accounts = response.get("Items", [])

        # Asegurarse de que 'saldo' sea tratado como string
        for account in accounts:
            account['saldo'] = str(account.get('saldo', "0"))  # Convertir saldo a string

        return {
            "statusCode": 200,
            "body": json.dumps(accounts),  # Ya no necesitamos 'default=decimal_default'
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
