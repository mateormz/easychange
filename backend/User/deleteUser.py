import os
import json
from singleton import get_dynamodb, get_lambda_client  # Usamos el singleton

def lambda_handler(event, context):
    try:
        print("[INFO] Received event:", json.dumps(event, indent=2))

        dynamodb = get_dynamodb()
        lambda_client = get_lambda_client()

        # Load environment variables
        try:
            user_table_name = os.environ['TABLE_USERS']
            validate_function_name = f"{os.environ['SERVICE_NAME']}-{os.environ['STAGE']}-{os.environ['VALIDATE_TOKEN_FUNCTION']}"
            print("[INFO] Environment variables loaded successfully")
            print(f"[DEBUG] User table name: {user_table_name}")
            print(f"[DEBUG] Validate function name: {validate_function_name}")
        except KeyError as env_error:
            print(f"[ERROR] Missing environment variable: {str(env_error)}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f"Missing environment variable: {str(env_error)}"})
            }

        user_table = dynamodb.Table(user_table_name)

        # Get Authorization token
        token = event.get('headers', {}).get('Authorization')
        print(f"[DEBUG] Authorization token: {token}")

        if not token:
            print("[WARNING] Authorization token is missing")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Authorization token is missing'})
            }

        # Validate token via Lambda
        payload = {"body": json.dumps({"token": token})}
        print("[INFO] Invoking validateToken function")
        validate_response = lambda_client.invoke(
            FunctionName=validate_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        validation_result = json.loads(validate_response['Payload'].read())
        print(f"[DEBUG] Validation result: {validation_result}")

        if validation_result.get('statusCode') != 200:
            print("[WARNING] Token validation failed")
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Unauthorized - Invalid or expired token'})
            }

        user_info = json.loads(validation_result.get('body', '{}'))
        authenticated_user_id = user_info.get('user_id')
        print(f"[INFO] Authenticated user_id: {authenticated_user_id}")

        # Get user_id from path
        try:
            user_id = event['pathParameters']['user_id']
            print(f"[INFO] Path parameter retrieved: user_id={user_id}")
        except KeyError as path_error:
            print(f"[ERROR] Missing path parameter: {str(path_error)}")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'Missing path parameter: {str(path_error)}'})
            }

        # Check ownership or if user is admin
        if user_id != authenticated_user_id:
            print("[INFO] Checking if user is admin")
            if user_info.get('role') != 'admin':
                print("[WARNING] User is attempting to delete unauthorized resource")
                return {
                    'statusCode': 403,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Unauthorized - You can only delete your own account unless you are an admin'})
                }

        # Check if user exists
        print(f"[INFO] Checking if user exists: user_id={user_id}")
        get_response = user_table.get_item(Key={'user_id': user_id})
        print(f"[DEBUG] get_item response: {get_response}")

        if 'Item' not in get_response:
            print("[WARNING] User not found")
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'User not found'})
            }

        # Delete the user
        print(f"[INFO] Deleting user from DynamoDB: user_id={user_id}")
        user_table.delete_item(Key={'user_id': user_id})

        print("[INFO] User deletion successful")
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'User deleted successfully'})
        }

    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal Server Error', 'details': str(e)})
        }
