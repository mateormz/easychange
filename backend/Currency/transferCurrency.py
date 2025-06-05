import boto3
import json
from common import (
    validate_token_and_get_user,
    get_account_by_id_from_profile,
    update_balance_in_profile,
    fetch_rate_for_pair_from_exchange
)

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

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

        from_account = get_account_by_id_from_profile(from_user_id, from_account_id)
        to_account = get_account_by_id_from_profile(to_user_id, to_account_id)

        if not from_account or not to_account:
            return respond(404, {'error': 'Account not found'})

        if from_account['saldo'] < amount:
            return respond(400, {'error': 'Insufficient balance in source account'})

        if transfer_currency:
            rate = float(fetch_rate_for_pair_from_exchange(from_currency, to_currency))
            converted_amount = amount * rate
        else:
            converted_amount = amount

        # Actualizaciones (idealmente se haría con transacciones)
        update_balance_in_profile(from_user_id, from_account_id, -amount)
        update_balance_in_profile(to_user_id, to_account_id, converted_amount)

        return respond(200, {
            'message': 'Transfer successful',
            'from_balance': from_account['saldo'] - amount,
            'to_balance': to_account['saldo'] + converted_amount
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
