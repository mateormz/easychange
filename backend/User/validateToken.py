import boto3
from datetime import datetime
import os
import json

def lambda_handler(event, context):
    try:
        print("[INFO] Received event:", json.dumps(event, indent=2))

        # Initialize DynamoDB
        dynamodb = boto3.resource('dynamodb')

        # Environment variable
        try:
            token_table_name = os.environ['TABLE_TOKENS']
            print("[INFO] Environment variable loaded successfully")
            print(f"[DEBUG] Token table name: {token_table_name}")
        except KeyError as env_error:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'Missing environment variable: {str(env_error)}'})
            }

        table = dynamodb.Table(token_table_name)

        # Get token from request body
        if not event.get('body'):
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Request body is missing'})
            }

        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError as e:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }

        token = body.get('token')
        if not token:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Token not provided'})
            }

        # Get token from table (by primary key)
        print(f"[INFO] Getting token from table: {token}")
        response = table.get_item(Key={'token': token})

        token_data = response.get('Item')
        if not token_data:
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid token'})
            }

        expiration = token_data.get('expiration')
        print(f"[DEBUG] Token expiration: {expiration}")

        if datetime.now().strftime('%Y-%m-%d %H:%M:%S') > expiration:
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Token expired'})
            }

        print("[INFO] Token is valid")

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'Token is valid',
                'expiration': expiration,
                'PK': token_data.get('PK')
            })
        }

    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal Server Error', 'details': str(e)})
        }