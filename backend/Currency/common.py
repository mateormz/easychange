import boto3
import os
import json
import time
import urllib.request
import urllib.parse

# Inicializa recursos
dynamodb = boto3.resource('dynamodb')
rates_table = dynamodb.Table(os.environ['RATES_TABLE'])
accounts_table = dynamodb.Table(os.environ["TABLE_BANKACC"])
lambda_client = boto3.client('lambda')

# Variables de entorno
API_URL = os.environ['EXTERNAL_API_URL']
API_KEY = os.environ['EXCHANGE_API_ACCESS_KEY']
CACHE_TTL = int(os.environ.get('CACHE_TTL_SECONDS', 3600))
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


# API EXCHANGE functions
def fetch_rate_for_pair_from_exchange(source, target):
    params = {
        'access_key': API_KEY,
        'source': source,
        'currencies': target
    }
    url = f"{API_URL}/live?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
    if not data.get('success'):
        raise Exception(f"API error: {data}")
    quotes = data['quotes']
    key = source + target
    if key not in quotes:
        raise Exception(f"Rate not found for {source}->{target}")
    return str(quotes[key]), data['timestamp']


# API PROFILE functions
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
