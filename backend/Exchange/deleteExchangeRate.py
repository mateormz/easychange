import json
from commonExchange import validate_token_and_get_user, delete_rate_from_db


def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        from_currency = event['pathParameters']['from'].upper()
        to_currency = event['pathParameters']['to'].upper()

        delete_rate_from_db(from_currency, to_currency)

        return respond(200, {
            'message': f'Rate {from_currency}->{to_currency} deleted',
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
