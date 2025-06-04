import boto3
import os
import json
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["TABLE_BANKACC"])

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)
        moneda = event['pathParameters']['moneda']

        response = table.query(
            IndexName='moneda-index',
            KeyConditionExpression=Key('moneda').eq(moneda)
        )

        cuentas_filtradas = [item for item in response.get("Items", []) if item.get("usuario_id") == user_id]

        for account in cuentas_filtradas:
            account['saldo'] = account.get('saldo', 0)

        return {
            "statusCode": 200,
            "body": json.dumps(cuentas_filtradas, default=decimal_default),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
