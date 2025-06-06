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

def get_account_balance_from_profile(user_id, account_id, token):
    """
    Llama a la Lambda del servicio de perfil para obtener las cuentas bancarias del usuario
    y luego filtra la cuenta específica para obtener el saldo.
    """
    function_name = f"{PROFILE_SERVICE_NAME}-{os.environ['STAGE']}-listarCuentas"  # Función para listar las cuentas

    # Verificar que user_id y account_id no sean vacíos
    if not user_id or not account_id:
        raise Exception(f"Missing user_id or account_id. user_id: {user_id}, account_id: {account_id}")

    # Preparar el payload para la invocación
    payload = {
        "pathParameters": {
            "user_id": user_id  # Aquí pasamos el user_id en los path parameters correctamente
        },
        "body": json.dumps({"account_id": account_id})  # Puede incluir otros parámetros en el cuerpo si es necesario
    }

    # El token debe ir dentro del payload, no en los headers
    token_payload = {
        "body": payload["body"],
        "headers": {"Authorization": token}  # El token aquí está en el payload
    }

    try:
        # Invocar la Lambda de cuentas
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(token_payload),  # Pasa el token en el payload
        )

        # Parsear la respuesta de la Lambda
        response_payload = json.loads(response['Payload'].read().decode())

        # Depuración: Imprimir la respuesta completa que se obtiene de la Lambda
        print(f"Response from profile service: {json.dumps(response_payload)}")  # Depuración

        # Verificar que la respuesta tenga una clave 'body' que contenga la lista de cuentas
        if 'body' not in response_payload:
            raise Exception("No body found in response.")

        # Obtener el contenido de 'body'
        body = response_payload['body']

        # Si body es una cadena, convertirlo a un objeto JSON
        if isinstance(body, str):
            try:
                body = json.loads(body)  # Convertirlo en un objeto JSON si es una cadena
            except json.JSONDecodeError:
                raise Exception("La respuesta en 'body' no es un JSON válido.")

        # Comprobar si body es un diccionario (en lugar de una lista)
        if isinstance(body, dict):
            body = [body]  # Convertir el diccionario a una lista que contenga ese diccionario

        # Verificar que estamos obteniendo una lista de cuentas
        if not isinstance(body, list):
            raise Exception(f"Expected a list of accounts, but got {type(body)}")

        # Verificar que tenemos cuentas
        if not body:
            raise Exception("No accounts found for the user.")

        # Depuración: Imprimir las cuentas recibidas
        print(f"Accounts: {json.dumps(body)}")  # Depuración

        # Buscar la cuenta correspondiente por account_id
        account = next((acc for acc in body if acc.get('cuenta_id') == account_id), None)

        if not account:
            raise Exception(f"Account with account_id {account_id} not found.")

        # Obtener saldo como cadena
        saldo = account.get('saldo', '0')

        # Convertir el saldo a float antes de devolverlo
        return float(saldo)  # Retornar el saldo como float

    except Exception as e:
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
