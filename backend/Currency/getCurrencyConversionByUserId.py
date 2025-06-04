import boto3
import json
import os
from common import validate_token_and_get_user
from boto3.dynamodb.conditions import Key  # ✅ IMPORT NECESARIO

# Singleton para DynamoDB resource
def get_dynamodb_resource():
    if not hasattr(get_dynamodb_resource, "_instance"):
        get_dynamodb_resource._instance = boto3.resource('dynamodb')
    return get_dynamodb_resource._instance

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(os.environ['USER_CONVERSIONS_TABLE'])

        response = table.query(
            KeyConditionExpression=Key('user_id').eq(user_id)
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
