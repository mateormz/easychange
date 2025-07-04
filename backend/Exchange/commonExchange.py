import boto3
import os
import json
import time
import urllib.request
import urllib.parse
from unittest.mock import patch


# Singleton para la configuración de la API externa (URL y API Key)
class ExchangeRateAPI:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExchangeRateAPI, cls).__new__(cls)
            cls._instance.api_url = os.environ['EXTERNAL_API_URL']
            cls._instance.api_key = os.environ['EXCHANGE_API_ACCESS_KEY']
            print("[INFO] Creando nueva instancia de ExchangeRateAPI")
        else:
            print("[INFO] Reutilizando la instancia de ExchangeRateAPI")
        return cls._instance

    def get_api_url(self):
        return self.api_url

    def get_api_key(self):
        return self.api_key

    def fetch_rates_for_source(self, source):
        """
        Obtiene todas las tasas de cambio desde 'source' usando la API externa.
        Retorna un diccionario con las tasas y el timestamp de la consulta.
        """
        params = {
            'access_key': self.api_key,
            'source': source
        }
        url = f"{self.api_url}/live?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
        if not data.get('success'):
            raise Exception(f"API error: {data}")
        if 'quotes' not in data:
            raise Exception("No exchange rates found in the API response.")
        return data['quotes'], data['timestamp']


# Función de prueba con mockeo
@patch('commonExchange.ExchangeRateAPI.fetch_rate_for_pair', return_value=('3.75', 'timestamp'))
def test_currency_conversion():
    # Esta función ahora devolverá 3.75 como tasa de cambio en lugar de hacer una llamada real
    # Aquí puedes realizar el test donde necesites esa tasa de cambio fija

    exchange_api = ExchangeRateAPI()
    rate, timestamp = exchange_api.fetch_rate_for_pair('USD', 'EUR')

    # Comprobamos si la tasa de cambio es la mockeada, que debe ser 3.75
    assert rate == '3.75'
    print(f'Tasa de cambio mockeada: {rate}, Timestamp: {timestamp}')


# Llamada a la función de prueba
test_currency_conversion()


# Singleton para la conexión a DynamoDB
class DynamoDBConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DynamoDBConnection, cls).__new__(cls)
            cls._instance.dynamodb = boto3.resource('dynamodb')
            cls._instance.table = cls._instance.dynamodb.Table(os.environ['RATES_TABLE'])
            print("[INFO] Creando nueva instancia de DynamoDB")
        else:
            print("[INFO] Reutilizando la instancia de DynamoDB")
        return cls._instance

    def get_table(self):
        return self.table


# Inicializa recurso DynamoDB y tabla (usando Singleton para la conexión)
dynamodb_connection = DynamoDBConnection()
table = dynamodb_connection.get_table()

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
