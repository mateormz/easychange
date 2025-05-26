import boto3
import os
import json
from boto3.dynamodb.conditions import Key
from common import validate_token_and_get_user
from decimal import Decimal
import requests

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["TABLE_CURRENCY_CONVERSION"])

EXCHANGE_API_BASE = "https://fm80rh9h9g.execute-api.us-east-1.amazonaws.com/dev/exchange-rate"

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        response = table.query(
            KeyConditionExpression=Key('usuario_id').eq(user_id)
        )

        items = response.get("Items", [])

        # Actualizar tasa con la API externa (opcional)
        for item in items:
            from_currency = item.get('from_currency')
            to_currency = item.get('to_currency')
            if from_currency and to_currency:
                url = f"{EXCHANGE_API_BASE}/{from_currency}/{to_currency}"
                res = requests.get(url)
                if res.status_code == 200:
                    data = res.json()
                    # Asumimos que el JSON tiene el rate en 'rate' o similar
                    item['rate'] = str(data.get('rate', item.get('rate')))

        return {
            "statusCode": 200,
            "body": json.dumps(items)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
