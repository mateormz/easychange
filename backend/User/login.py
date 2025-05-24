import boto3
import hashlib
import uuid
from datetime import datetime, timedelta
import os
from boto3.dynamodb.conditions import Key
import json

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def lambda_handler(event, context):
    try:
        print("[INFO] Received event:", json.dumps(event, indent=2))

        # Initialize DynamoDB
        dynamodb = boto3.resource('dynamodb')

        # Environment variables
        try:
            user_table_name = os.environ['TABLE_USERS']
            token_table_name = os.environ['TABLE_TOKENS']
            email_index = os.environ['INDEX_EMAIL_USERS']
            print("[INFO] Environment variables loaded successfully")
            print(f"[DEBUG] User table: {user_table_name}")
            print(f"[DEBUG] Token table: {token_table_name}")
            print(f"[DEBUG] Email index: {email_index}")
        except KeyError as env_error:
            print(f"[ERROR] Missing environment variable: {str(env_error)}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f"Missing environment variable: {str(env_error)}"})
            }

        user_table = dynamodb.Table(user_table_name)
        token_table = dynamodb.Table(token_table_name)

        # Parse request body
        if 'body' not in event or not event['body']:
            print("[WARNING] Request body is missing")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Request body is missing'})
            }

        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON body: {str(e)}")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }

        email = body.get('email')
        password = body.get('password')

        print(f"[DEBUG] Parsed email: {email}")
        print(f"[DEBUG] Parsed password: {'*' * len(password) if password else None}")

        if not all([email, password]):
            print("[WARNING] Missing required fields")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Missing required fields'})
            }

        hashed_password = hash_password(password)
        print(f"[DEBUG] Hashed password: {hashed_password}")

        # Query the user by email
        print(f"[INFO] Querying user by email: {email}")
        response = user_table.query(
            IndexName=email_index,
            KeyConditionExpression=Key('email').eq(email)
        )
        print(f"[DEBUG] Query response: {response}")

        if not response['Items']:
            print("[WARNING] Email not found")
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid credentials'})
            }

        user = response['Items'][0]

        if user['password_hash'] != hashed_password:
            print("[WARNING] Password mismatch")
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid credentials'})
            }

        user_id = user['user_id']
        role = user.get('role', 'distributor')

        # Generate token
        token = str(uuid.uuid4())
        expiration = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

        print(f"[INFO] Token generated: {token}")
        print(f"[DEBUG] Token expiration: {expiration}")

        # Save token in DB
        print("[INFO] Storing token in DynamoDB")
        token_table.put_item(
            Item={
                'token': token,
                'expiration': expiration,
                'user_id': user_id,
                'role': role
            }
        )

        print("[INFO] Login successful")
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'token': token,
                'expires': expiration,
                'user_id': user_id,
                'role': role
            })
        }

    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal Server Error', 'details': str(e)})
        }