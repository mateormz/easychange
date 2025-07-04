import boto3
import os
import json
import time
from commonExchange import validate_token_and_get_user, get_rate_from_db, save_rate_to_db
from commonExchange import ExchangeRateAPI, DynamoDBConnection  # Importa los Singleton


def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        from_currency = event['pathParameters']['from'].upper()
        to_currency = event['pathParameters']['to'].upper()

        # Diccionario con tasas de cambio personalizadas
        fixed_rates = {
            'USDEUR': '0.84',  # USD a EUR
            'EURUSD': '1.19',  # EUR a USD
            'USDPEN': '3.75',  # USD a PEN
            'PENUSD': '0.27',  # PEN a USD
            'USDJPY': '110.45',  # USD a JPY
            'JPYNZD': '1.40',  # JPY a NZD
        }

        # Usa DynamoDBConnection
        db_connection = DynamoDBConnection()
        table = db_connection.get_table()

        # Combinamos las dos monedas
        currency_pair = from_currency + to_currency

        # Verificamos si el par está en el diccionario
        if currency_pair in fixed_rates:
            rate = fixed_rates[currency_pair]
            timestamp = int(time.time())  # Timestamp actual
        else:

            rate = '1.00'  # Tasa predeterminada
            timestamp = int(time.time())
            save_rate_to_db(from_currency, to_currency, rate, timestamp)

        save_rate_to_db(from_currency, to_currency, rate, timestamp)

        # Respuesta de la API
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

