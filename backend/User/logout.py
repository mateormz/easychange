import boto3
import os
import json

def lambda_handler(event, context):
    try:
        print("[INFO] Received event:", json.dumps(event, indent=2))

        dynamodb = boto3.resource('dynamodb')

        # Load environment variables
        try:
            token_table_name = os.environ['TABLE_TOKENS']
            print("[INFO] Environment variables loaded successfully")
            print(f"[DEBUG] Token table: {token_table_name}")
        except KeyError as env_error:
            print(f"[ERROR] Missing environment variable: {str(env_error)}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f"Missing environment variable: {str(env_error)}"})
            }

        token_table = dynamodb.Table(token_table_name)

        # Get token from header
        token = event.get('headers', {}).get('Authorization')
        print(f"[DEBUG] Authorization token: {token}")

        if not token:
            print("[WARNING] Authorization token is missing")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Authorization token is missing'})
            }

        # Check if token exists
        print("[INFO] Checking if token exists in DynamoDB")
        get_response = token_table.get_item(Key={'token': token})
        print(f"[DEBUG] get_item response: {get_response}")

        if 'Item' not in get_response:
            print("[WARNING] Token not found in table")
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Token not found or already invalidated'})
            }

        # Delete token
        print("[INFO] Deleting token from DynamoDB")
        token_table.delete_item(Key={'token': token})

        print("[INFO] Logout successful")
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'Logout successful. Token invalidated.'})
        }

    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal Server Error', 'details': str(e)})
        }