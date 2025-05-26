import json
import time
from commonExchange import validate_token_and_get_user, get_rate_from_db, fetch_rate_for_pair, save_rate_to_db

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        from_currency = event['pathParameters']['from'].upper()
        to_currency = event['pathParameters']['to'].upper()

        record = get_rate_from_db(from_currency, to_currency)
        now = int(time.time())

        if record:
            if now > record['ttl']:
                rate, timestamp = fetch_rate_for_pair(from_currency, to_currency)
                save_rate_to_db(from_currency, to_currency, rate, timestamp)
            else:
                rate = record['rate']
        else:
            rate, timestamp = fetch_rate_for_pair(from_currency, to_currency)
            save_rate_to_db(from_currency, to_currency, rate, timestamp)

        return respond(200, {
            'from': from_currency,
            'to': to_currency,
            'rate': rate,
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
