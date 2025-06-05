import os
import json
from singleton import get_dynamodb, get_lambda_client

def lambda_handler(event, context):
    try:
        print("[INFO] Received event:", json.dumps(event, indent=2))

        dynamodb = get_dynamodb()
        lambda_client = get_lambda_client()

        try:
            user_table_name = os.environ['TABLE_USERS']
            validate_function_name = f"{os.environ['SERVICE_NAME']}-{os.environ['STAGE']}-{os.environ['VALIDATE_TOKEN_FUNCTION']}"
            print("[INFO] Environment variables loaded successfully")
        except KeyError as env_error:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f"Missing environment variable: {str(env_error)}"})
            }

        user_table = dynamodb.Table(user_table_name)

        # Obtener el token desde el cuerpo de la solicitud
        body = json.loads(event.get('body', '{}'))  # Asegurarse de parsear el cuerpo correctamente
        token = body.get('token')

        if not token:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Authorization token is missing'})
            }

        # Realizar la validación del token
        payload = {"body": json.dumps({"token": token})}
        validate_response = lambda_client.invoke(
            FunctionName=validate_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        validation_result = json.loads(validate_response['Payload'].read())

        if validation_result.get('statusCode') != 200:
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Unauthorized - Invalid or expired token'})
            }

        user_info = json.loads(validation_result.get('body', '{}'))
        authenticated_user_id = user_info.get('user_id')

        try:
            user_id = event['pathParameters']['user_id']
        except KeyError as path_error:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'Missing path parameter: {str(path_error)}'})
            }

        if user_id != authenticated_user_id:
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Unauthorized - You can only access your own account'})
            }

        response = user_table.get_item(Key={'user_id': user_id})
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'User not found'})
            }

        user = response['Item']
        user.pop('password_hash', None)  # Remove sensitive info

        # Aquí se añade el rol del usuario
        user_role = user.get('role', 'user')  # Default to 'user' if no role exists
        user['role'] = user_role  # Add role to the response

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(user)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal Server Error', 'details': str(e)})
        }
