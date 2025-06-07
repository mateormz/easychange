import boto3
import json
import uuid
import os
from datetime import datetime, timezone
from common import (
    validate_token_and_get_user,
    fetch_rate_for_pair_from_exchange,
    get_account_balance_from_profile,
    update_balance_in_profile,
    add_money_to_account_in_profile,
    call_get_currency_date_limit,  # <-- Importa función para fecha límite
    call_get_currency_limit        # <-- Importa función para límite de monto
)

lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['USER_CONVERSIONS_TABLE'])


def lambda_handler(event, context):
    try:
        token = event.get('headers', {}).get('Authorization')
        if not token:
            return respond(400, {'error': 'Authorization token is missing'})

        user_id = validate_token_and_get_user(event)

        body = json.loads(event.get('body', '{}'))
        from_user_id = body.get('fromUserId')
        to_user_id = body.get('toUserId')
        from_account_id = body.get('fromAccountId')
        to_account_id = body.get('toAccountId')
        amount = body.get('amount')
        from_currency = body.get('fromCurrency')
        to_currency = body.get('toCurrency')

        if not all([from_user_id, to_user_id, from_account_id, to_account_id, amount, from_currency, to_currency]):
            return respond(400, {'error': 'All fields are required'})
        if not isinstance(amount, (int, float)) or amount <= 0:
            return respond(400, {'error': 'Amount must be a positive number'})

        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        transfer_currency = from_currency != to_currency

        # Validar fecha límite para cambio de divisas
        try:
            currency_date_limit_resp = call_get_currency_date_limit(token)
            date_limit_str = currency_date_limit_resp.get('date_limit')
            if date_limit_str:
                date_limit = datetime.fromisoformat(date_limit_str).replace(tzinfo=timezone.utc)
                now = datetime.utcnow().replace(tzinfo=timezone.utc)
                if now > date_limit:
                    return respond(400, {'error': 'Currency exchange transactions are no longer allowed after the date limit'})
        except Exception as e:
            return respond(500, {'error': f'Error validating currency date limit: {str(e)}'})

        # Validar límite máximo por transacción
        try:
            currency_limit_resp = call_get_currency_limit(token)
            max_amount_usd = float(currency_limit_resp.get('amount', 0))
            limit_currency = currency_limit_resp.get('currency_type', 'USD').upper()

            amount_in_usd = amount
            if from_currency != 'USD':
                # Obtener tasa de cambio para convertir amount a USD y comparar
                rate_to_usd = float(fetch_rate_for_pair_from_exchange(from_currency, 'USD', token))
                amount_in_usd = amount * rate_to_usd

            if amount_in_usd > max_amount_usd:
                return respond(400, {'error': f'Transaction amount exceeds the maximum allowed limit of {max_amount_usd} USD'})
        except Exception as e:
            return respond(500, {'error': f'Error validating currency limit: {str(e)}'})

        try:
            from_balance = float(get_account_balance_from_profile(from_user_id, from_account_id, token))
            to_balance = float(get_account_balance_from_profile(to_user_id, to_account_id, token))
        except Exception as e:
            return respond(500, {'error': f'Error fetching account balance: {str(e)}'})

        if from_balance < amount:
            return respond(400, {'error': 'Insufficient balance in source account'})

        converted_amount = amount
        exchange_rate = None

        if transfer_currency:
            try:
                rate = float(fetch_rate_for_pair_from_exchange(from_currency, to_currency, token))
                converted_amount = amount * rate
                exchange_rate = rate
            except Exception as e:
                return respond(500, {'error': f'Error fetching exchange rate: {str(e)}'})

        transaction_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        new_from_balance = from_balance - amount

        try:
            # Restar amount a la cuenta fuente
            update_balance_in_profile(from_account_id, new_from_balance, token)

            # Sumar amount a la cuenta destino usando Lambda
            result = add_money_to_account_in_profile(to_account_id, to_user_id, converted_amount, token)

            if result.get('statusCode') != 200:
                raise Exception(f"Failed to add money to destination account: {result.get('body')}")

            # Guardar transacción en DynamoDB
            table.put_item(
                Item={
                    'user_id': str(from_user_id),
                    'timestamp': timestamp,
                    'transaction_id': transaction_id,
                    'from_account_id': str(from_account_id),
                    'to_user_id': str(to_user_id),
                    'to_account_id': str(to_account_id),
                    'amount': str(amount),
                    'converted_amount': str(converted_amount),
                    'from_currency': from_currency,
                    'to_currency': to_currency,
                    'exchange_rate': str(exchange_rate) if exchange_rate is not None else None,
                    'status': 'success'
                }
            )

        except Exception as e:
            return respond(500, {'error': f'Error updating balances: {str(e)}'})

        return respond(200, {
            'message': 'Transfer successful',
            'fromUserBalance': new_from_balance,
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
