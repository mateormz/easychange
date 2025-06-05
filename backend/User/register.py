import hashlib
import uuid
from datetime import datetime, timedelta
import os
import json
from boto3.dynamodb.conditions import Key
from singleton import get_dynamodb  # Importa la instancia Singleton de DynamoDB

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def lambda_handler(event, context):
    try:
        print("[INFO] Received event:", json.dumps(event, indent=2))

        # Obtener instancia Singleton de DynamoDB
        dynamodb = get_dynamodb()

        # Variables de entorno
        try:
            user_table_name = os.environ['TABLE_USERS']
            token_table_name = os.environ['TABLE_TOKENS']
            email_index = os.environ['INDEX_EMAIL_USERS']
            print("[INFO] Environment variables loaded successfully")
        except KeyError as env_error:
            print(f"[ERROR] Missing environment variable: {str(env_error)}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f"Missing environment variable: {str(env_error)}"})
            }

        user_table = dynamodb.Table(user_table_name)
        token_table = dynamodb.Table(token_table_name)

        # Parsear cuerpo
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
        name = body.get('name')
        lastName = body.get('lastName')
        phoneNumber = body.get('phoneNumber')
        dni = body.get('dni')
        role = body.get('role', 'user')  # Añadido campo de rol

        print(f"[DEBUG] Email: {email}, Name: {name}, LastName: {lastName}, Phone: {phoneNumber}, DNI: {dni}, Role: {role}")

        if not all([email, password, name, lastName, phoneNumber, dni]):
            print("[WARNING] Missing required fields")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Missing required fields'})
            }

        # Verificar si el email ya existe
        print(f"[INFO] Checking if email is already registered: {email}")
        response = user_table.query(
            IndexName=email_index,
            KeyConditionExpression=Key('email').eq(email)
        )

        if response['Items']:
            print("[WARNING] Email is already registered")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'The email is already registered'})
            }

        # Crear usuario
        user_id = str(uuid.uuid4())
        item = {
            'user_id': user_id,
            'email': email,
            'password_hash': hash_password(password),
            'name': name,
            'lastName': lastName,
            'phoneNumber': phoneNumber,
            'dni': dni,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'role': role  # Se guarda el rol
        }

        print(f"[INFO] Saving user: {item}")
        user_table.put_item(Item=item)

        # Crear token
        token = str(uuid.uuid4())
        expiration = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[INFO] Token generated: {token}")

        token_table.put_item(
            Item={
                'token': token,
                'expiration': expiration,
                'user_id': user_id
            }
        )

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'token': token,
                'expires': expiration,
                'user_id': user_id
            })
        }

    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal Server Error', 'details': str(e)})
        }
