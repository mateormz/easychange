
import boto3
import os
import json
import uuid
from commonExchange import validate_token_and_get_user, save_rates_to_db
from commonExchange import ExchangeRateAPI, DynamoDBConnection  # Importa los Singleton

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        body = json.loads(event.get('body', '{}'))
        source = body.get('from')
        if not source:
            return respond(400, {'error': 'Missing "from" currency in body'})

        # Usa ExchangeRateAPI Singleton para consultar la API externa
        exchange_api = ExchangeRateAPI()
        quotes, timestamp = exchange_api.fetch_rates_for_source(source.upper())

        # Usa DynamoDBConnection Singleton para obtener la referencia a la tabla
        db_connection = DynamoDBConnection()
        table = db_connection.get_table()

        save_rates_to_db(quotes, timestamp)

        return respond(201, {
            'message': f'Rates for {source} created/updated',
            'user_id': user_id
        })
    except Exception as e:
        return respond(500, {'error': str(e)})


def respond(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }
