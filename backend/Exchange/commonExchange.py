import boto3
import os
import json
import time
import urllib.request
import urllib.parse

# Inicializa recurso DynamoDB y tabla
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['RATES_TABLE'])

# Variables de entorno para la API externa y TTL
API_URL = os.environ['EXTERNAL_API_URL']
API_KEY = os.environ['EXCHANGE_API_ACCESS_KEY']
CACHE_TTL = int(os.environ.get('CACHE_TTL_SECONDS', 3600))


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
    return user_info.get('user_id')


def fetch_rates_for_source(source):
    """
    Obtiene todas las tasas de cambio desde 'source' usando la API externa.
    Retorna un diccionario con las tasas y el timestamp de la consulta.
    """
    params = {
        'access_key': API_KEY,
        'source': source
    }
    url = f"{API_URL}/live?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
    if not data.get('success'):
        raise Exception(f"API error: {data}")
    return data['quotes'], data['timestamp']


def fetch_rate_for_pair(source, target):
    """
    Obtiene la tasa puntual de cambio entre source y target desde la API externa.
    """
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
    return str(quotes[key]), data['timestamp']  # guardamos como string


def save_rates_to_db(quotes, timestamp):
    """
    Guarda o reemplaza las tasas en DynamoDB, borrando primero las existentes para la moneda origen.
    """
    source = None
    for key in quotes.keys():
        source = key[:3]
        break
    if source is None:
        raise Exception("Could not determine source currency")

    # Borra tasas antiguas
    delete_rates_by_source(source)

    now = int(time.time())
    ttl = now + CACHE_TTL

    with table.batch_writer() as batch:
        for key, rate in quotes.items():
            from_currency = key[:3]
            to_currency = key[3:]
            batch.put_item(Item={
                'from': from_currency,
                'to': to_currency,
                'rate': str(rate),  # guardamos como string
                'fetched_at': now,
                'expiration': timestamp,
                'ttl': ttl
            })


def delete_rates_by_source(from_currency):
    """
    Borra todas las tasas que tienen como moneda origen 'from_currency'.
    """
    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('from').eq(from_currency)
    )
    with table.batch_writer() as batch:
        for item in response.get('Items', []):
            batch.delete_item(Key={'from': item['from'], 'to': item['to']})


def get_rate_from_db(from_currency, to_currency):
    """
    Obtiene la tasa almacenada en DynamoDB para el par (from_currency, to_currency).
    Retorna None si no existe.
    """
    response = table.get_item(Key={'from': from_currency, 'to': to_currency})
    return response.get('Item')


def save_rate_to_db(from_currency, to_currency, rate, timestamp):
    """
    Guarda o actualiza una tasa puntual en DynamoDB.
    """
    now = int(time.time())
    ttl = now + CACHE_TTL
    table.put_item(Item={
        'from': from_currency,
        'to': to_currency,
        'rate': str(rate),  # guardamos como string
        'fetched_at': now,
        'expiration': timestamp,
        'ttl': ttl
    })


def delete_rate_from_db(from_currency, to_currency):
    """
    Elimina una tasa puntual del par (from_currency, to_currency) en DynamoDB.
    """
    table.delete_item(Key={'from': from_currency, 'to': to_currency})
