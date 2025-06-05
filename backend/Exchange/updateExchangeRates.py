import json
from commonExchange import validate_token_and_get_user, save_rates_to_db
from commonExchange import ExchangeRateAPI, DynamoDBConnection  # Importa los Singleton

def lambda_handler(event, context):
    try:
        # Validar token y obtener user_id
        user_id = validate_token_and_get_user(event)

        # Leer moneda origen del body
        body = json.loads(event.get('body', '{}'))
        from_currency = body.get('from')
        if not from_currency:
            return respond(400, {'error': '"from" currency is required in body'})

        from_currency = from_currency.upper()

        # Obtener todas las tasas desde la API externa
        exchange_api = ExchangeRateAPI()  # Usa el Singleton para la API
        quotes, timestamp = exchange_api.fetch_rates_for_source(from_currency)

        # Usar el Singleton para la conexión a DynamoDB
        db_connection = DynamoDBConnection()  # Obtienes la misma instancia
        table = db_connection.get_table()

        # Guardar tasas en la base de datos
        save_rates_to_db(quotes, timestamp)

        return respond(200, {
            'message': f'Todas las tasas desde {from_currency} actualizadas',
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