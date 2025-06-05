
import boto3
import os
import uuid
import json
import time
from commonExchange import validate_token_and_get_user, get_rate_from_db, save_rate_to_db
from commonExchange import ExchangeRateAPI, DynamoDBConnection  # Importa los Singleton

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        from_currency = event['pathParameters']['from'].upper()
        to_currency = event['pathParameters']['to'].upper()

        # Usa DynamoDBConnection Singleton para obtener la referencia a la tabla
        db_connection = DynamoDBConnection()
        table = db_connection.get_table()

        # Intenta obtener la tasa de la base de datos
        record = get_rate_from_db(from_currency, to_currency)
        now = int(time.time())

        # Si la tasa está en la base de datos
        if record:
            # Si el TTL ya ha expirado, realiza una nueva consulta a la API externa
            if now > record['ttl']:
                # Usa ExchangeRateAPI Singleton para consultar la API externa
                exchange_api = ExchangeRateAPI()  # Instancia del Singleton
                rate, timestamp = exchange_api.fetch_rate_for_pair(from_currency, to_currency)
                save_rate_to_db(from_currency, to_currency, rate, timestamp)
            else:
                rate = record['rate']
        else:
            # Si no hay registro, realiza la consulta a la API externa
            exchange_api = ExchangeRateAPI()  # Instancia del Singleton
            rate, timestamp = exchange_api.fetch_rate_for_pair(from_currency, to_currency)
            save_rate_to_db(from_currency, to_currency, rate, timestamp)

        return respond(200, {
            'from': from_currency,
            'to': to_currency,
            'rate': rate,
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
