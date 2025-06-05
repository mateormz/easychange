import json
from common import validate_token_and_get_user, fetch_rate_for_pair_from_exchange

def lambda_handler(event, context):
    try:
        # Obtener el token del encabezado de la solicitud
        token = event.get('headers', {}).get('Authorization')
        if not token:
            return respond(400, {'error': 'Authorization token is missing'})

        # Validar el token y obtener el user_id
        user_id = validate_token_and_get_user(event)

        # Parsear el cuerpo del evento
        body = json.loads(event.get('body', '{}'))
        from_currency = body.get('fromCurrency')
        to_currency = body.get('toCurrency')
        amount = body.get('amount')

        # Validaciones de entrada
        if not from_currency or not to_currency:
            return respond(400, {'error': 'fromCurrency and toCurrency are required'})
        if amount is None or not isinstance(amount, (int, float)) or amount <= 0:
            return respond(400, {'error': 'amount must be a positive number'})

        # Convertir las monedas a mayúsculas
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # Llamada a la función Lambda para obtener la tasa de cambio
        # Ahora pasamos el token en los encabezados de la invocación
        rate = float(fetch_rate_for_pair_from_exchange(from_currency, to_currency, token))

        # Calcular la cantidad convertida
        converted_amount = float(amount) * rate

        # Responder con la conversión
        return respond(200, {
            'user_id': user_id,
            'fromCurrency': from_currency,
            'toCurrency': to_currency,
            'amount': amount,
            'convertedAmount': round(converted_amount, 2),
            'exchangeRate': rate
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
