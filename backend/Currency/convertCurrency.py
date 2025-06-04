import json
from common import validate_token_and_get_user, fetch_rate_for_pair_from_exchange


def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        body = json.loads(event.get('body', '{}'))
        from_currency = body.get('fromCurrency').upper()
        to_currency = body.get('toCurrency').upper()
        amount = body.get('amount')

        if not amount or amount <= 0:
            return respond(400, {'error': 'Invalid amount'})

        # Obtener la tasa de cambio de API EXCHANGE
        rate, timestamp = fetch_rate_for_pair_from_exchange(from_currency, to_currency)

        # Calcular el monto convertido
        converted_amount = float(amount) * float(rate)

        return respond(200, {
            'user_id': user_id,
            'fromCurrency': from_currency,
            'toCurrency': to_currency,
            'amount': amount,
            'convertedAmount': converted_amount,
            'exchangeRate': rate,
            'timestamp': timestamp
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
