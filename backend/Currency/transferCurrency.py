import boto3
import json
from common import validate_token_and_get_user, get_account_by_id_from_profile, update_balance_in_profile
from common import fetch_rate_for_pair_from_exchange

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        body = json.loads(event.get('body', '{}'))
        from_user_id = body.get('fromUserId')
        to_user_id = body.get('toUserId')
        from_account_id = body.get('fromAccountId')
        to_account_id = body.get('toAccountId')
        amount = body.get('amount')
        from_currency = body.get('fromCurrency').upper()
        to_currency = body.get('toCurrency').upper()
        transfer_currency = body.get('transferCurrency', False)

        # Obtener cuentas de API PROFILE
        from_account = get_account_by_id_from_profile(from_user_id, from_account_id)
        to_account = get_account_by_id_from_profile(to_user_id, to_account_id)

        if not from_account or not to_account:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Account not found'})
            }

        if transfer_currency:
            # Convertir moneda si es necesario usando API EXCHANGE
            rate, timestamp = fetch_rate_for_pair_from_exchange(from_currency, to_currency)
            converted_amount = amount * float(rate)
        else:
            converted_amount = amount  # Sin conversión

        # Actualizar saldo de las cuentas en API PROFILE
        update_balance_in_profile(from_user_id, from_account_id, -amount)
        update_balance_in_profile(to_user_id, to_account_id, converted_amount)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Transfer successful',
                'from_balance': from_account['saldo'] - amount,
                'to_balance': to_account['saldo'] + converted_amount
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
