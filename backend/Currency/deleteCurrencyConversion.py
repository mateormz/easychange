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

        # Obtener item para saber from y to currencies
        response = table.get_item(
            Key={
                'usuario_id': user_id,
                'conversion_id': conversion_id
            }
        )
        item = response.get('Item')
        if not item:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Conversión no encontrada'})
            }

        from_currency = item.get('from_currency')
        to_currency = item.get('to_currency')

        # Llamada a API externa para eliminar tasa
        if from_currency and to_currency:
            url = f"{EXCHANGE_API_BASE}/{from_currency}/{to_currency}"
            res = requests.delete(url)
            if res.status_code != 200:
                raise Exception(f"Error eliminando tasa en EXCHANGE API: {res.text}")

        # Eliminar de Dynamo
        table.delete_item(
            Key={
                'usuario_id': user_id,
                'conversion_id': conversion_id
            }
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Conversión eliminada exitosamente'})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
