import boto3
import os
import json
import urllib.request
import urllib.error

# Recursos globales
lambda_client = boto3.client('lambda')

# Variables de entorno
EXCHANGE_SERVICE_NAME = os.environ['EXCHANGE_SERVICE_NAME']
PROFILE_SERVICE_NAME = os.environ['PROFILE_SERVICE_NAME']


def validate_token_and_get_user(event):
    """
    Valida el token de autorización en el header 'Authorization' invocando la lambda validateToken.
    Retorna user_id si es válido o lanza excepción en caso contrario.
    """
    # Obtener el token del encabezado
    token = event.get('headers', {}).get('Authorization')
    if not token:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Token no proporcionado"})
        }

    # Llamada a la Lambda de validación de token
    validate_function_name = f"{os.environ['SERVICE_NAME']}-{os.environ['STAGE']}-{os.environ['VALIDATE_TOKEN_FUNCTION']}"

    # Preparar la carga útil para invocar la función Lambda
    token_payload = {
        "body": json.dumps({"token": token})
    }

    try:
        # Invocar la función Lambda que valida el token
        response = lambda_client.invoke(
            FunctionName=validate_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(token_payload)
        )
        # Parsear la respuesta de la Lambda
        validation_result = json.loads(response['Payload'].read().decode())

        if validation_result.get('statusCode') != 200:
            return {
                "statusCode": validation_result.get('statusCode'),
                "body": validation_result.get('body')
            }

        # Obtener el user_id del cuerpo de la respuesta
        user_info = json.loads(validation_result.get('body', '{}'))
        return user_info.get('user_id')

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error al validar el token: {str(e)}"})
        }


def fetch_rate_for_pair_from_exchange(source, target):
    """
    Llama a la función Lambda del servicio de cambio de divisas para obtener la tasa de cambio entre dos monedas.
    """
    # Usamos el nuevo nombre de la función Lambda 'exchange-rate-api-dev-consultConversion'
    function_name = f"exchange-rate-api-{os.environ['STAGE']}-consultConversion"  # Nombre de la función Lambda que consulta las tasas
    payload = {
        "pathParameters": {
            "from": source,
            "to": target
        }
    }

    try:
        # Invocar la función Lambda que devuelve la tasa de cambio
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',  # Llamada síncrona
            Payload=json.dumps(payload)
        )

        # Leer la respuesta
        response_payload = json.loads(response['Payload'].read().decode())

        # Verificar si la respuesta tiene una tasa de cambio válida
        if response_payload.get('statusCode') != 200:
            raise Exception(f"Error al obtener la tasa de cambio: {response_payload.get('body')}")

        # Devolver la tasa de cambio
        data = json.loads(response_payload.get('body'))
        if "rate" not in data:
            raise Exception(f"Tasa de cambio no encontrada para {source}->{target}")

        return str(data["rate"])

    except Exception as e:
        raise Exception(f"Failed to fetch exchange rate via Lambda: {str(e)}")


def get_account_by_id_from_profile(user_id, account_id):
    """
    Llama a la función Lambda del servicio de perfil para obtener la cuenta bancaria de un usuario.
    """
    function_name = f"{PROFILE_SERVICE_NAME}-{os.environ['STAGE']}-listBankAccounts"
    payload = {"body": json.dumps({"user_id": user_id, "account_id": account_id})}
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    result = json.loads(response['Payload'].read())
    return result


def update_balance_in_profile(user_id, account_id, amount):
    """
    Llama a la función Lambda del servicio de perfil para actualizar el saldo de una cuenta bancaria.
    """
    function_name = f"{PROFILE_SERVICE_NAME}-{os.environ['STAGE']}-updateBankAccount"
    payload = {"body": json.dumps({
        "user_id": user_id,
        "account_id": account_id,
        "amount": amount
    })}
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    result = json.loads(response['Payload'].read())
    return result
