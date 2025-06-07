import boto3
import os
import json

# Singleton para el cliente Lambda
class LambdaClientSingleton:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = boto3.client('lambda')
        return cls._client

# Variables de entorno
EXCHANGE_SERVICE_NAME = os.environ['EXCHANGE_SERVICE_NAME']
PROFILE_SERVICE_NAME = os.environ['PROFILE_SERVICE_NAME']

def validate_token_and_get_user(event):
    token = event.get('headers', {}).get('Authorization')
    print(f"Token extraído del encabezado: {token}")

    if not token:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Token no proporcionado"})
        }

    validate_function_name = f"{os.environ['SERVICE_NAME']}-{os.environ['STAGE']}-{os.environ['VALIDATE_TOKEN_FUNCTION']}"

    token_payload = {
        "body": json.dumps({"token": token})
    }

    try:
        response = LambdaClientSingleton.get_client().invoke(
            FunctionName=validate_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(token_payload)
        )
        validation_result = json.loads(response['Payload'].read().decode())
        print(f"Respuesta de validación del token: {validation_result}")

        if validation_result.get('statusCode') != 200:
            return {
                "statusCode": validation_result.get('statusCode'),
                "body": validation_result.get('body')
            }

        user_info = json.loads(validation_result.get('body', '{}'))
        return user_info.get('user_id')

    except Exception as e:
        print(f"Error al validar el token: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error al validar el token: {str(e)}"})
        }

def fetch_rate_for_pair_from_exchange(source, target, token):
    function_name = f"exchange-rate-api-{os.environ['STAGE']}-consultConversion"
    payload = {
        "pathParameters": {
            "from": source,
            "to": target
        },
        "headers": {
            "Authorization": token
        }
    }

    try:
        response = LambdaClientSingleton.get_client().invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        response_payload = json.loads(response['Payload'].read().decode())

        if response_payload.get('statusCode') != 200:
            raise Exception(f"Error al obtener la tasa de cambio: {response_payload.get('body')}")

        data = json.loads(response_payload.get('body'))
        if "rate" not in data:
            raise Exception(f"Tasa de cambio no encontrada para {source}->{target}")

        return str(data["rate"])

    except Exception as e:
        raise Exception(f"Failed to fetch exchange rate via Lambda: {str(e)}")

def get_account_balance_from_profile(user_id, account_id, token):
    function_name = f"{PROFILE_SERVICE_NAME}-{os.environ['STAGE']}-listarCuentas"

    if not user_id or not account_id:
        raise Exception(f"Missing user_id or account_id. user_id: {user_id}, account_id: {account_id}")

    payload = {
        "pathParameters": {
            "user_id": user_id
        },
        "body": json.dumps({"account_id": account_id})
    }

    token_payload = {
        "pathParameters": payload["pathParameters"],
        "body": payload["body"],
        "headers": {"Authorization": token}
    }

    try:
        response = LambdaClientSingleton.get_client().invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(token_payload),
        )

        response_payload = json.loads(response['Payload'].read().decode())
        print(f"Response from profile service: {json.dumps(response_payload)}")

        if 'body' not in response_payload:
            raise Exception("No body found in response.")

        body = response_payload['body']

        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                raise Exception("La respuesta en 'body' no es un JSON válido.")

        if isinstance(body, dict):
            body = [body]

        if not isinstance(body, list):
            raise Exception(f"Expected a list of accounts, but got {type(body)}")

        if not body:
            raise Exception("No accounts found for the user.")

        print(f"Accounts: {json.dumps(body)}")

        account = next((acc for acc in body if acc.get('cuenta_id') == account_id), None)

        if not account:
            raise Exception(f"Account with account_id {account_id} not found.")

        amount = account.get('amount', '0')

        return float(amount)

    except Exception as e:
        raise Exception(f"Error fetching account balance: {str(e)}")

def update_balance_in_profile(account_id, new_balance, token):
    function_name = f"{PROFILE_SERVICE_NAME}-{os.environ['STAGE']}-actualizarCuenta"

    payload = {
        "body": json.dumps({
            "amount": str(new_balance)
        }),
        "pathParameters": {
            "cuenta_id": account_id
        },
        "headers": {
            "Authorization": token
        }
    }

    try:
        response = LambdaClientSingleton.get_client().invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload),
        )

        result = json.loads(response['Payload'].read().decode())
        return result

    except Exception as e:
        raise Exception(f"Error al actualizar el monto de la cuenta: {str(e)}")

def add_money_to_account_in_profile(account_id, user_id, amount, token):
    function_name = f"{PROFILE_SERVICE_NAME}-{os.environ['STAGE']}-addMoneyToBankAccount"

    payload = {
        "body": json.dumps({
            "usuario_id": user_id,
            "bankAccId": account_id,
            "amount": str(amount)
        }),
        "headers": {
            "Authorization": token
        }
    }

    try:
        response = LambdaClientSingleton.get_client().invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload),
        )

        result = json.loads(response['Payload'].read().decode())
        return result

    except Exception as e:
        raise Exception(f"Error al agregar dinero a la cuenta destino: {str(e)}")

def call_get_currency_date_limit(token):
    function_name = f"{os.environ['ADMIN_SERVICE_NAME']}-{os.environ['STAGE']}-getCurrencyDateLimit"

    payload = {
        'headers': {
            'Authorization': token
        }
    }

    response = LambdaClientSingleton.get_client().invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )

    result = json.loads(response['Payload'].read())

    if result.get('statusCode') == 200:
        return json.loads(result['body'])
    else:
        raise Exception(f"Error al obtener currency date limit: {result.get('body')}")

def call_get_currency_limit(token):
    function_name = f"{os.environ['ADMIN_SERVICE_NAME']}-{os.environ['STAGE']}-getCurrencyLimit"

    payload = {
        'headers': {
            'Authorization': token
        }
    }

    response = LambdaClientSingleton.get_client().invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )

    result = json.loads(response['Payload'].read())

    if result.get('statusCode') == 200:
        return json.loads(result['body'])
    else:
        raise Exception(f"Error al obtener currency limit: {result.get('body')}")
