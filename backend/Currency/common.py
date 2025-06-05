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
    print(f"Token extraído del encabezado: {token}")  # Registro para depuración

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

        print(f"Respuesta de validación del token: {validation_result}")  # Registro para depuración

        if validation_result.get('statusCode') != 200:
            return {
                "statusCode": validation_result.get('statusCode'),
                "body": validation_result.get('body')
            }

        # Obtener el user_id del cuerpo de la respuesta
        user_info = json.loads(validation_result.get('body', '{}'))
        return user_info.get('user_id')

    except Exception as e:
        print(f"Error al validar el token: {str(e)}")  # Registro para depuración
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error al validar el token: {str(e)}"})
        }


def fetch_rate_for_pair_from_exchange(source, target, token):
    """
    Llama a la función Lambda del servicio de cambio de divisas para obtener la tasa de cambio entre dos monedas.
    """
    function_name = f"exchange-rate-api-{os.environ['STAGE']}-consultConversion"  # Nombre de la función Lambda que consulta las tasas
    payload = {
        "pathParameters": {
            "from": source,
            "to": target
        },
        "headers": {
            "Authorization": token  # Pasamos el token dentro del payload
        }
    }

    try:
        # Invocar la función Lambda que devuelve la tasa de cambio
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',  # Llamada síncrona
            Payload=json.dumps(payload)  # El token ahora está dentro del payload
        )

        # Leer la respuesta
        response_payload = json.loads(response['Payload'].read().decode())

        if response_payload.get('statusCode') != 200:
            raise Exception(f"Error al obtener la tasa de cambio: {response_payload.get('body')}")

        # Devolver la tasa de cambio
        data = json.loads(response_payload.get('body'))
        if "rate" not in data:
            raise Exception(f"Tasa de cambio no encontrada para {source}->{target}")

        return str(data["rate"])

    except Exception as e:
        raise Exception(f"Failed to fetch exchange rate via Lambda: {str(e)}")


import json
import logging

# Configuración del logger para obtener detalles más claros
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def get_account_balance_from_profile(user_id, account_id, token):
    """
    Llama a la Lambda del servicio de perfil para obtener las cuentas bancarias del usuario
    y luego filtra la cuenta específica para obtener el saldo.
    """
    function_name = f"{PROFILE_SERVICE_NAME}-{os.environ['STAGE']}-listarCuentas"  # Función para listar las cuentas
    logger.info(f"Invocando Lambda con FunctionName: {function_name} y user_id: {user_id}")  # Log de la invocación

    # Preparar el payload para la invocación
    payload = {
        "body": json.dumps({"user_id": user_id})  # Pasamos el user_id para obtener las cuentas
    }
    logger.info(f"Payload enviado a la Lambda: {json.dumps(payload)}")  # Log del payload

    # El token debe ir dentro del payload, no en los headers
    token_payload = {
        "body": payload["body"],
        "headers": {"Authorization": token}  # El token aquí está en el payload
    }

    try:
        # Invocar la Lambda de cuentas
        logger.info(f"Invocando Lambda para obtener cuentas con token: {token[:10]}...")  # Log del token (solo los primeros 10 caracteres por seguridad)
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(token_payload),  # Pasa el token en el payload
        )

        # Parsear la respuesta de la Lambda
        response_payload = json.loads(response['Payload'].read().decode())
        logger.info(f"Respuesta de la Lambda: {json.dumps(response_payload)}")  # Log de la respuesta

        # Verificar que la respuesta tenga una clave 'body' que contenga la lista de cuentas
        if 'body' not in response_payload:
            raise Exception("No body found in response.")

        body = response_payload.get('body', [])
        logger.info(f"Cuentas obtenidas: {json.dumps(body)}")  # Log de las cuentas obtenidas

        if isinstance(body, str):
            body = json.loads(body)  # Si es cadena, convertirla a JSON

        # Verificar que tenemos cuentas
        if not body:
            raise Exception("No accounts found for the user.")
        logger.info(f"Cuentas válidas encontradas para el usuario: {user_id}")

        # Buscar la cuenta correspondiente por account_id
        account = next((acc for acc in body if acc['cuenta_id'] == account_id), None)
        logger.info(f"Buscando cuenta con account_id: {account_id}...")  # Log de búsqueda de la cuenta

        if not account:
            raise Exception(f"Account with account_id {account_id} not found.")

        # Log del saldo de la cuenta encontrada
        logger.info(f"Saldo encontrado para la cuenta {account_id}: {account.get('saldo', 0)}")

        # Retornar el saldo de la cuenta
        return float(account.get('saldo', 0))  # Retornar el saldo como float

    except Exception as e:
        logger.error(f"Error al obtener el saldo de la cuenta: {str(e)}")  # Log del error
        raise Exception(f"Error fetching account balance: {str(e)}")



def update_balance_in_profile(user_id, account_id, amount, token):
    """
    Actualiza el saldo de una cuenta bancaria del usuario invocando la Lambda correspondiente
    en el servicio de perfil. El token de autorización se pasa en los encabezados.
    """
    function_name = f"{PROFILE_SERVICE_NAME}-{os.environ['STAGE']}-actualizarCuenta"

    # Preparar el cuerpo del payload sin el token
    payload = {
        "body": json.dumps({
            "user_id": user_id,
            "account_id": account_id,
            "amount": amount
        })
    }

    # Poner el token dentro del payload
    token_payload = {
        "body": payload["body"],
        "headers": {"Authorization": token}  # Incluir el token aquí dentro del payload
    }

    try:
        # Invocar la Lambda de actualización de saldo
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',  # Llamada síncrona
            Payload=json.dumps(token_payload),  # Pasa el token dentro del payload
        )

        # Leer la respuesta de la Lambda
        result = json.loads(response['Payload'].read().decode())

        # Devolver el resultado de la invocación
        return result

    except Exception as e:
        raise Exception(f"Error al actualizar el saldo de la cuenta: {str(e)}")


