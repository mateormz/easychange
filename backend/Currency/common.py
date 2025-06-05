import boto3
import os
import json
import urllib.request
import urllib.error

# Recursos globales
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

# Variables de entorno
API_KEY = os.environ['EXCHANGE_API_ACCESS_KEY']
EXCHANGE_SERVICE_NAME = os.environ['EXCHANGE_SERVICE_NAME']
PROFILE_SERVICE_NAME = os.environ['PROFILE_SERVICE_NAME']

def validate_token_and_get_user(event):
    token = event.get('headers', {}).get('Authorization')
    if not token:
        raise Exception("Authorization token is missing")

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
    return user_info.get('user_id')


def fetch_rate_for_pair_from_exchange(source, target):
    exchange_base_url = os.environ['EXCHANGE_API_URL']  # Este valor ya incluye /dev si usas ImportValue correctamente
    url = f"{exchange_base_url}/exchange-rate/{source}/{target}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

        if "rate" not in data:
            raise Exception(f"Rate not found in response from Exchange API for {source}->{target}")

        return str(data["rate"])

    except urllib.error.HTTPError as e:
        raise Exception(f"Exchange API error {e.code}: {e.read().decode()}")
    except Exception as e:
        raise Exception(f"Failed to fetch exchange rate: {str(e)}")


def get_account_by_id_from_profile(user_id, account_id):
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
