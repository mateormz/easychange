import json
from commonExchange import validate_token_and_get_user, fetch_rate_for_pair, save_rate_to_db


def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        from_currency = event['pathParameters']['from'].upper()
        to_currency = event['pathParameters']['to'].upper()

        rate, timestamp = fetch_rate_for_pair(from_currency, to_currency)
        save_rate_to_db(from_currency, to_currency, rate, timestamp)

        return respond(200, {
            'message': f'Rate {from_currency}->{to_currency} updated',
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
