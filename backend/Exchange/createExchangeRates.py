import json
from commonExchange import validate_token_and_get_user, fetch_rates_for_source, save_rates_to_db


def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        body = json.loads(event.get('body', '{}'))
        source = body.get('from')
        if not source:
            return respond(400, {'error': 'Missing "from" currency in body'})

        quotes, timestamp = fetch_rates_for_source(source.upper())
        save_rates_to_db(quotes, timestamp)

        return respond(201, {
            'message': f'Rates for {source} created/updated',
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
