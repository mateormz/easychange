import os
import json
from singleton import get_dynamodb, get_lambda_client  # Singleton imports

def lambda_handler(event, context):
    try:
        print("[INFO] Received event:", json.dumps(event, indent=2))

        # Usar instancias Singleton
        dynamodb = get_dynamodb()
        lambda_client = get_lambda_client()

        # Cargar variables de entorno
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

        # Obtener token
        token = event.get('headers', {}).get('Authorization')
        print(f"[DEBUG] Authorization token: {token}")

        if not token:
            print("[WARNING] Authorization token is missing")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Authorization token is missing'})
            }

        # Validar token
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

        # Obtener user_id del path
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

        # Verificación de autorización
        if user_id != authenticated_user_id:
            print("[WARNING] User is attempting to update unauthorized resources")
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Unauthorized - You can only update your own account'})
            }

        # Verificar existencia del usuario
        print(f"[INFO] Checking if user exists: user_id={user_id}")
        user_check = user_table.get_item(Key={'user_id': user_id})
        print(f"[DEBUG] get_item response: {user_check}")

        if 'Item' not in user_check:
            print("[WARNING] User not found")
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'User not found'})
            }

        # Parsear body
        try:
            body = json.loads(event.get('body', '{}'))
            print(f"[DEBUG] Body parsed: {body}")
        except json.JSONDecodeError as decode_error:
            print(f"[ERROR] Failed to parse body: {str(decode_error)}")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }

        if not body:
            print("[WARNING] Request body is empty")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Request body is missing'})
            }

        # Construir expresión de actualización
        update_expression = "SET " + ", ".join(f"#{k} = :{k}" for k in body)
        expression_attribute_names = {f"#{k}": k for k in body}
        expression_attribute_values = {f":{k}": v for k, v in body.items()}

        # Actualizar en DynamoDB
        print("[INFO] Updating user in DynamoDB")
        user_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )

        print("[INFO] User updated successfully")
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'User updated successfully'})
        }

    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal Server Error', 'details': str(e)})
        }