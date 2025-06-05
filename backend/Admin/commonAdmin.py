import boto3
import json
import os

# Singleton para la conexión a DynamoDB
class DynamoDBConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DynamoDBConnection, cls).__new__(cls)
            cls._instance.dynamodb = boto3.resource('dynamodb')
            print("[INFO] Creando nueva instancia de DynamoDB")
        else:
            print("[INFO] Reutilizando la instancia de DynamoDB")
        return cls._instance

    def get_table(self, table_name):
        return self.dynamodb.Table(table_name)


# Función para validar el token y obtener el user_id
def validate_token_and_get_user(event):
    """
    Valida el token de autorización en el header 'Authorization' invocando la lambda validateToken.
    Retorna user_id si es válido o lanza excepción en caso contrario.
    """
    token = event.get('headers', {}).get('Authorization')
    if not token:
        raise Exception("Authorization token is missing")

    lambda_client = boto3.client('lambda')
    validate_function_name = f"{os.environ['SERVICE_NAME']}-{os.environ['STAGE']}-{os.environ['VALIDATE_TOKEN_FUNCTION']}"

    payload = {"body": json.dumps({"token": token})}
    response = lambda_client.invoke(
        FunctionName=validate_function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    validation_result = json.loads(response['Payload'].read())

    if validation_result.get('statusCode') != 200:
        raise Exception("Unauthorized - Invalid or expired token")

    user_info = json.loads(validation_result.get('body', '{}'))
    return user_info.get('user_id'), token


# Función para obtener el rol del usuario usando su user_id
def get_user_role_by_user_id(user_id, token):
    """
    Invoca la función getUserById de la API de usuario para obtener el rol del usuario, 
    incluyendo el token en los headers para autenticar la invocación.
    """
    lambda_client = boto3.client('lambda')
    user_function_name = f"{os.environ['USER_SERVICE_NAME']}-{os.environ['STAGE']}-getUserById"  # Reemplaza con el nombre real de la función de la API de usuario

    payload = {
        'pathParameters': {
            'user_id': user_id
        }
    }

    # Configurar los encabezados con el token
    headers = {
        'Authorization': token
    }

    # Invoca la función Lambda getUserById, pasando los encabezados con el token
    response = lambda_client.invoke(
        FunctionName=user_function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload),
        Headers=headers  # Pasamos el token en los headers
    )

    user_info = json.loads(response['Payload'].read())

    if user_info.get('statusCode') == 200:
        user_data = json.loads(user_info.get('body'))
        return user_data.get('role', 'user')  # Default to 'user' if no role exists
    else:
        raise Exception("User not found or unable to fetch user info")
