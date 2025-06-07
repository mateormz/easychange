import boto3
import json
import uuid
import os
from datetime import datetime
from common import (
    validate_token_and_get_user,
    fetch_rate_for_pair_from_exchange,
    get_account_balance_from_profile,
    update_balance_in_profile,
    add_money_to_account_in_profile  # ✅ función correcta
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
            # ✅ Restar amount a la cuenta fuente
            update_balance_in_profile(from_account_id, new_from_balance, token)

            # ✅ Sumar amount a la cuenta destino usando Lambda
            result = add_money_to_account_in_profile(to_account_id, to_user_id, converted_amount, token)

            if result.get('statusCode') != 200:
                raise Exception(f"Failed to add money to destination account: {result.get('body')}")

            # ✅ Guardar transacción en DynamoDB
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
