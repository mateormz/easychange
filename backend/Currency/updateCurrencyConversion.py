import boto3
import os
import json
from common import validate_token_and_get_user
import requests

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["TABLE_CURRENCY_CONVERSION"])

EXCHANGE_API_BASE = "https://fm80rh9h9g.execute-api.us-east-1.amazonaws.com/dev/exchange-rate"

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)
        conversion_id = event['pathParameters']['conversion_id']
        body = json.loads(event.get('body', '{}'))

        if not body:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Request body is missing'})
            }

        # Convertir rate a string si existe
        if 'rate' in body:
            body['rate'] = str(body['rate'])

        # Llamada a API externa para actualizar tasa específica
        from_currency = body.get('from_currency')
        to_currency = body.get('to_currency')

        if from_currency and to_currency:
            url = f"{EXCHANGE_API_BASE}/{from_currency}/{to_currency}"
            res = requests.put(url, json=body)
            if res.status_code != 200:
                raise Exception(f"Error actualizando tasa en EXCHANGE API: {res.text}")
        else:
            # Si solo se actualiza 'from', llamar update-exchangerates
            if 'from_currency' in body:
                res = requests.post(f"{EXCHANGE_API_BASE}/update", json={"from": body['from_currency']})
                if res.status_code != 200:
                    raise Exception(f"Error actualizando tasas en EXCHANGE API: {res.text}")

        update_expression = "SET " + ", ".join(f"#{k} = :{k}" for k in body)
        expression_attribute_names = {f"#{k}": k for k in body}
        expression_attribute_values = {f":{k}": v for k, v in body.items()}

        table.update_item(
            Key={
                'usuario_id': user_id,
                'conversion_id': conversion_id
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Conversión actualizada exitosamente'})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
