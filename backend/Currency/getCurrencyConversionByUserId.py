import boto3
import json
from common import validate_token_and_get_user

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['USER_CONVERSIONS_TABLE'])

        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
        )

        transactions = response.get('Items', [])

        return respond(200, {'transactions': transactions})

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
