import boto3
import json
import uuid
from datetime import datetime
from common import (
    validate_token_and_get_user,
    fetch_rate_for_pair_from_exchange,
    get_account_balance_from_profile,  # Llamada correcta a la función
    update_balance_in_profile
)

lambda_client = boto3.client('lambda')

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
        from_user_id = body.get('fromUserId')
        to_user_id = body.get('toUserId')
        from_account_id = body.get('fromAccountId')
        to_account_id = body.get('toAccountId')
        amount = body.get('amount')
        from_currency = body.get('fromCurrency')
        to_currency = body.get('toCurrency')
        transfer_currency = body.get('transferCurrency', False)

        # Validaciones de los campos de entrada
        if not all([from_user_id, to_user_id, from_account_id, to_account_id, amount, from_currency, to_currency]):
            return respond(400, {'error': 'All fields are required'})
        if not isinstance(amount, (int, float)) or amount <= 0:
            return respond(400, {'error': 'Amount must be a positive number'})

        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # Obtener el saldo de las cuentas del usuario
        try:
            # Obtener saldo de las cuentas de origen y destino
            from_balance = get_account_balance_from_profile(from_user_id, from_account_id, token)
            to_balance = get_account_balance_from_profile(to_user_id, to_account_id, token)
        except Exception as e:
            return respond(500, {'error': f'Error fetching account balance: {str(e)}'})

        # Verificar que el saldo de la cuenta de origen sea suficiente
        if from_balance < amount:
            return respond(400, {'error': 'Insufficient balance in source account'})

        # Calcular la conversión si es necesario
        converted_amount = amount
        exchange_rate = None

        if transfer_currency:
            # Llamada a la función Lambda para obtener la tasa de cambio
            try:
                rate = float(fetch_rate_for_pair_from_exchange(from_currency, to_currency, token))
                converted_amount = amount * rate
                exchange_rate = rate  # Guardar la tasa de cambio utilizada
            except Exception as e:
                return respond(500, {'error': f'Error fetching exchange rate: {str(e)}'})

        # Crear un transactionId único para la transacción
        transaction_id = str(uuid.uuid4())

        # Registrar la fecha y hora de la transacción
        timestamp = datetime.utcnow().isoformat()

        # Actualizar el saldo de las cuentas (con transacciones ideales)
        try:
            update_balance_in_profile(from_user_id, from_account_id, -amount, token)
            update_balance_in_profile(to_user_id, to_account_id, converted_amount, token)
        except Exception as e:
            return respond(500, {'error': f'Error updating balance: {str(e)}'})

        # Preparar la respuesta
        return respond(200, {
            'message': 'Transfer successful',
            'fromUserBalance': from_balance - amount,
            'toUserBalance': to_balance + converted_amount,
            'transactionId': transaction_id,
            'amountTransferred': amount,
            'exchangeRate': exchange_rate,
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
