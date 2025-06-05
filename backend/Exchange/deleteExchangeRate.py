
import boto3
import os
import json
import uuid
import json
from commonExchange import validate_token_and_get_user, delete_rate_from_db
from commonExchange import DynamoDBConnection  # Importa el Singleton para la conexión a DynamoDB

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        from_currency = event['pathParameters']['from'].upper()
        to_currency = event['pathParameters']['to'].upper()

        # Usa DynamoDBConnection Singleton para obtener la referencia a la tabla
        db_connection = DynamoDBConnection()
        table = db_connection.get_table()

        delete_rate_from_db(from_currency, to_currency)

        return respond(200, {
            'message': f'Rate {from_currency}->{to_currency} deleted',
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
