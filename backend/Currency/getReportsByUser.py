import boto3
import json
import os
from common import validate_token_and_get_user

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        dynamodb = boto3.resource('dynamodb')
        report_table = dynamodb.Table(os.environ['USER_REPORTS_TABLE'])

        response = report_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
        )

        reports = response.get('Items', [])

        return respond(200, {'reports': reports})

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
