import boto3
import os
import json


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
    Invoca la Lambda del servicio de perfil que lista las cuentas del usuario
    autenticado mediante el token, y filtra por 'account_id' para obtener el saldo.
    """
    function_name = f"{PROFILE_SERVICE_NAME}-{os.environ['STAGE']}-listarCuentas"

    # Validar que el account_id no esté vacío (user_id ya no se requiere aquí)
    if not account_id:
        raise Exception(f"Missing account_id: {account_id}")

    # Construir el "event" simulado que se enviará a la Lambda del servicio de perfil
    event_payload = {
        "headers": {
            "Authorization": token
        }
    }

    try:
        # Invocar la Lambda remota que lista las cuentas
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(event_payload),
        )

        # Leer y decodificar el resultado
        response_payload = json.loads(response['Payload'].read().decode())

        print(f"Respuesta desde Lambda de perfil: {json.dumps(response_payload)}")

        # Verificar que la respuesta tenga statusCode 200
        if response_payload.get("statusCode") != 200:
            raise Exception(f"Error de la Lambda de perfil: {response_payload.get('body')}")

        # Obtener el cuerpo y asegurarse de que sea una lista
        body = response_payload.get("body", "[]")
        try:
            accounts = json.loads(body)
        except json.JSONDecodeError:
            raise Exception("La respuesta en 'body' no es un JSON válido.")

        if not isinstance(accounts, list):
            raise Exception("Se esperaba una lista de cuentas.")

        if not accounts:
            raise Exception("No se encontraron cuentas para el usuario.")

        print(f"Cuentas recibidas: {json.dumps(accounts)}")

        # Buscar la cuenta correspondiente
        account = next((acc for acc in accounts if acc.get('cuenta_id') == account_id), None)

        if not account:
            raise Exception(f"No se encontró la cuenta con ID {account_id}.")

        # Obtener y convertir el saldo
        amount = account.get('amount', '0')
        return float(amount)

    except Exception as e:
        raise Exception(f"Error al obtener el saldo de la cuenta: {str(e)}")


def update_balance_in_profile(account_id, new_balance, token):
    """
    Actualiza el monto (amount) de una cuenta bancaria invocando la Lambda correspondiente.
    Se pasa el nuevo monto como string, conforme lo espera el servicio Profile.
    """
    function_name = f"{PROFILE_SERVICE_NAME}-{os.environ['STAGE']}-actualizarCuenta"

    payload = {
        "body": json.dumps({
            "amount": str(new_balance)  # Enviamos el nuevo monto como string
        }),
        "pathParameters": {
            "cuenta_id": account_id
        },
        "headers": {
            "Authorization": token
        }
    }

    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload),
        )

        result = json.loads(response['Payload'].read().decode())
        return result

    except Exception as e:
        raise Exception(f"Error al actualizar el monto de la cuenta: {str(e)}")



def add_money_to_account_in_profile(account_id, user_id, amount, token):
    """
    Agrega dinero a una cuenta bancaria invocando la Lambda `addMoneyToBankAccount`.
    Esta función debe usarse para la cuenta destino en una transferencia.
    """
    function_name = f"{PROFILE_SERVICE_NAME}-{os.environ['STAGE']}-addMoneyToBankAccount"

    payload = {
        "body": json.dumps({
            "usuario_id": user_id,
            "bankAccId": account_id,
            "amount": str(amount)  # ✅ Clave unificada
        }),
        "headers": {
            "Authorization": token
        }
    }

    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload),
        )

        result = json.loads(response['Payload'].read().decode())
        return result

    except Exception as e:
        raise Exception(f"Error al agregar dinero a la cuenta destino: {str(e)}")
