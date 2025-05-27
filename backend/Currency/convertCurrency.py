import boto3
import os
import json
import uuid
import urllib.request
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["TABLE_CURRENCY_CONVERSION"])

EXCHANGE_API_BASE = "https://fm80rh9h9g.execute-api.us-east-1.amazonaws.com/dev/exchange-rate"

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)
        body = json.loads(event.get('body', '{}'))

        from_currency = body['from_currency']
        to_currency = body['to_currency']
        rate = str(body['rate'])

        # Llamada a EXCHANGE API usando urllib en vez de requests
        url = f"{EXCHANGE_API_BASE}/create"
        payload = json.dumps({"from": from_currency}).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    raise Exception(f"Error en EXCHANGE API: status {response.status}")
                response_body = response.read().decode("utf-8")
                print("EXCHANGE API response:", response_body)
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTPError al llamar EXCHANGE API: {e.code} - {e.read().decode('utf-8')}")

        conversion_id = str(uuid.uuid4())

        item = {
            "usuario_id": user_id,
            "conversion_id": conversion_id,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": rate
        }

        table.put_item(Item=item)

        return {
            'statusCode': 201,
            'body': json.dumps({'message': 'Conversión creada con éxito', 'conversion_id': conversion_id})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
