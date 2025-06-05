import boto3
import json
import uuid
from datetime import datetime
from common import (
    validate_token_and_get_user,
    fetch_rate_for_pair_from_exchange
)

lambda_client = boto3.client('lambda')


def get_account_balance_from_profile(user_id, account_id):
    """
    Llama a la Lambda del servicio de perfil para obtener las cuentas bancarias del usuario
    y luego filtra la cuenta específica para obtener el saldo.
    """
    function_name = "easychange-profile-api-dev-listBankAccounts"  # Nombre de la función Lambda que consulta las cuentas
    payload = {
        "body": json.dumps({"user_id": user_id})  # Pasamos el user_id para obtener las cuentas
    }

    try:
        # Invocar la Lambda de cuentas
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        # Parsear la respuesta de la Lambda
        response_payload = json.loads(response['Payload'].read().decode())

        # Verificar que la respuesta tenga cuentas
        accounts = response_payload.get('body', [])
        if not accounts:
            raise Exception("No accounts found for the user.")

        # Buscar la cuenta correspondiente por account_id
        account = next((acc for acc in accounts if acc['account_id'] == account_id), None)
        if not account:
            raise Exception("Account not found.")

        # Retornar el saldo de la cuenta
        return account.get('saldo', 0)  # Si no tiene saldo, retorna 0

    except Exception as e:
        raise Exception(f"Error fetching account balance: {str(e)}")


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

        # Validaciones
        if not all([from_user_id, to_user_id, from_account_id, to_account_id, amount, from_currency, to_currency]):
            return respond(400, {'error': 'All fields are required'})
        if not isinstance(amount, (int, float)) or amount <= 0:
            return respond(400, {'error': 'Amount must be a positive number'})

        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # Obtener el saldo de las cuentas del usuario
        from_balance = get_account_balance_from_profile(from_user_id, from_account_id)
        to_balance = get_account_balance_from_profile(to_user_id, to_account_id)

        if from_balance < amount:
            return respond(400, {'error': 'Insufficient balance in source account'})

        # Calcular la conversión si es necesario
        converted_amount = amount
        exchange_rate = None

        if transfer_currency:
            # Llamada a la función Lambda para obtener la tasa de cambio
            rate = float(fetch_rate_for_pair_from_exchange(from_currency, to_currency, token))
            converted_amount = amount * rate
            exchange_rate = rate  # Guardar la tasa de cambio utilizada

        # Crear un transactionId único para la transacción
        transaction_id = str(uuid.uuid4())

        # Registrar la fecha y hora de la transacción
        timestamp = datetime.utcnow().isoformat()

        # Actualizaciones (idealmente se haría con transacciones)
        update_balance_in_profile(from_user_id, from_account_id, -amount)
        update_balance_in_profile(to_user_id, to_account_id, converted_amount)

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
