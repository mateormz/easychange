import os
import json
import pytest
import boto3
from moto import mock_dynamodb
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import time

# Configurar todas las variables de entorno necesarias antes de importar commonExchange
@pytest.fixture(autouse=True)
def setup_environment():
    """Configurar variables de entorno para todos los tests"""
    env_vars = {
        "CACHE_TTL_SECONDS": "3600",
        "RATES_TABLE": "dev-exchange-rates",
        "EXTERNAL_API_URL": "https://api.exchangerate.host",
        "EXCHANGE_API_ACCESS_KEY": "test_key",
        "SERVICE_NAME": "test-service",
        "STAGE": "dev",
        "VALIDATE_TOKEN_FUNCTION": "validateToken",
        "AWS_DEFAULT_REGION": "us-east-1"  # Agregar región de AWS
    }
    
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture
def dynamodb_table():
    """Fixture para crear tabla DynamoDB mockeada"""
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = os.environ["RATES_TABLE"]
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'from', 'KeyType': 'HASH'},
                {'AttributeName': 'to', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'from', 'AttributeType': 'S'},
                {'AttributeName': 'to', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        yield table


def test_save_and_get_rate_from_db(dynamodb_table):
    """Test para guardar y obtener una tasa individual"""
    from Exchange import commonExchange as common

    from_currency = 'USD'
    to_currency = 'PEN'
    rate = '3.75'
    timestamp = int(time.time())

    # Guardar tasa en la tabla
    common.save_rate_to_db(from_currency, to_currency, rate, timestamp)

    # Obtener tasa desde la tabla
    data = common.get_rate_from_db(from_currency, to_currency)

    assert data is not None
    assert data['rate'] == rate
    assert data['from'] == from_currency
    assert data['to'] == to_currency
    assert data['expiration'] == timestamp


def test_delete_rate_from_db(dynamodb_table):
    """Test para eliminar una tasa individual"""
    from Exchange import commonExchange as common

    from_currency = 'USD'
    to_currency = 'PEN'
    rate = '3.75'
    timestamp = int(time.time())

    # Guardar tasa primero
    common.save_rate_to_db(from_currency, to_currency, rate, timestamp)

    # Verificar que existe
    assert common.get_rate_from_db(from_currency, to_currency) is not None

    # Eliminar
    common.delete_rate_from_db(from_currency, to_currency)

    # Verificar que ya no existe
    assert common.get_rate_from_db(from_currency, to_currency) is None


def test_save_rates_to_db(dynamodb_table):
    """Test para guardar múltiples tasas desde una fuente"""
    from Exchange import commonExchange as common

    # Datos de prueba en el formato que espera tu código
    quotes = {'USDPEN': 3.75, 'USDEUR': 0.9, 'USDJPY': 150.5}
    timestamp = int(time.time())

    # Guardar tasas
    common.save_rates_to_db(quotes, timestamp)

    # Verificar que se guardaron correctamente
    item1 = common.get_rate_from_db('USD', 'PEN')
    item2 = common.get_rate_from_db('USD', 'EUR')
    item3 = common.get_rate_from_db('USD', 'JPY')

    assert item1 is not None
    assert item1['rate'] == '3.75'
    assert item2 is not None
    assert item2['rate'] == '0.9'
    assert item3 is not None
    assert item3['rate'] == '150.5'


def test_save_rates_to_db_empty_quotes():
    """Test para manejar el caso cuando no hay quotes (línea 131)"""
    from Exchange import commonExchange as common

    # Quotes vacío debería lanzar excepción
    quotes = {}
    timestamp = int(time.time())

    with pytest.raises(Exception) as exc_info:
        common.save_rates_to_db(quotes, timestamp)
    
    assert "Could not determine source currency" in str(exc_info.value)


def test_delete_rates_by_source(dynamodb_table):
    """Test para eliminar todas las tasas de una moneda origen"""
    from Exchange import commonExchange as common

    timestamp = int(time.time())

    # Insertar datos de prueba directamente
    common.save_rate_to_db("USD", "PEN", "3.75", timestamp)
    common.save_rate_to_db("USD", "EUR", "0.9", timestamp)
    common.save_rate_to_db("EUR", "JPY", "130.5", timestamp)

    # Eliminar todas las tasas de USD
    common.delete_rates_by_source("USD")

    # Verificar que las tasas de USD se eliminaron
    assert common.get_rate_from_db("USD", "PEN") is None
    assert common.get_rate_from_db("USD", "EUR") is None
    
    # Verificar que las tasas de EUR siguen existiendo
    assert common.get_rate_from_db("EUR", "JPY") is not None


@patch("urllib.request.urlopen")
def test_fetch_rate_for_pair(mock_urlopen):
    """Test para obtener una tasa específica de la API externa"""
    from Exchange import commonExchange as common

    # Mock de la respuesta de la API
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "success": True,
        "quotes": {"USDPEN": 3.75},
        "timestamp": 1720000000
    }).encode()
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    # Crear instancia de la API
    api = common.ExchangeRateAPI()
    
    # Obtener tasa
    rate, timestamp = api.fetch_rate_for_pair("USD", "PEN")

    assert rate == "3.75"
    assert timestamp == 1720000000


@patch("urllib.request.urlopen")
def test_fetch_rates_for_source(mock_urlopen):
    """Test para obtener todas las tasas de una moneda origen"""
    from Exchange import commonExchange as common

    # Mock de la respuesta de la API
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "success": True,
        "quotes": {"USDPEN": 3.75, "USDEUR": 0.9, "USDJPY": 150.5},
        "timestamp": 1720000000
    }).encode()
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    # Crear instancia de la API
    api = common.ExchangeRateAPI()
    
    # Obtener tasas
    quotes, timestamp = api.fetch_rates_for_source("USD")

    assert "USDPEN" in quotes
    assert quotes["USDPEN"] == 3.75
    assert quotes["USDEUR"] == 0.9
    assert quotes["USDJPY"] == 150.5
    assert timestamp == 1720000000


@patch("urllib.request.urlopen")
def test_api_error_handling(mock_urlopen):
    """Test para manejo de errores de la API"""
    from Exchange import commonExchange as common

    # Mock de respuesta con error
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "success": False,
        "error": {"code": 104, "info": "Invalid access key"}
    }).encode()
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    api = common.ExchangeRateAPI()
    
    # Verificar que se lanza excepción
    with pytest.raises(Exception) as exc_info:
        api.fetch_rate_for_pair("USD", "PEN")
    
    assert "API error" in str(exc_info.value)


@patch("urllib.request.urlopen")
def test_rate_not_found_error(mock_urlopen):
    """Test para error cuando no se encuentra la tasa específica"""
    from Exchange import commonExchange as common

    # Mock de respuesta exitosa pero sin la tasa solicitada
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "success": True,
        "quotes": {"USDEUR": 0.9},  # No incluye USDPEN
        "timestamp": 1720000000
    }).encode()
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    api = common.ExchangeRateAPI()
    
    # Verificar que se lanza excepción cuando no existe la tasa
    with pytest.raises(Exception) as exc_info:
        api.fetch_rate_for_pair("USD", "PEN")
    
    assert "Rate not found for USD->PEN" in str(exc_info.value)


@patch("urllib.request.urlopen")
def test_fetch_rates_no_quotes_error(mock_urlopen):
    """Test para error cuando no hay quotes en la respuesta"""
    from Exchange import commonExchange as common

    # Mock de respuesta exitosa pero sin quotes
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "success": True,
        "timestamp": 1720000000
        # No incluye 'quotes'
    }).encode()
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    api = common.ExchangeRateAPI()
    
    # Verificar que se lanza excepción cuando no hay quotes
    with pytest.raises(Exception) as exc_info:
        api.fetch_rates_for_source("USD")
    
    assert "No exchange rates found in the API response" in str(exc_info.value)


@patch("urllib.request.urlopen")
def test_fetch_rates_api_error(mock_urlopen):
    """Test para error de API en fetch_rates_for_source"""
    from Exchange import commonExchange as common

    # Mock de respuesta con error
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "success": False,
        "error": {"code": 104, "info": "Invalid access key"}
    }).encode()
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    api = common.ExchangeRateAPI()
    
    # Verificar que se lanza excepción
    with pytest.raises(Exception) as exc_info:
        api.fetch_rates_for_source("USD")
    
    assert "API error" in str(exc_info.value)


def test_singleton_pattern():
    """Test para verificar que los singletons funcionan correctamente"""
    from Exchange import commonExchange as common
    
    # Crear múltiples instancias
    api1 = common.ExchangeRateAPI()
    api2 = common.ExchangeRateAPI()
    
    db1 = common.DynamoDBConnection()
    db2 = common.DynamoDBConnection()
    
    # Verificar que son la misma instancia
    assert api1 is api2
    assert db1 is db2


def test_exchange_rate_api_getters():
    """Test para cubrir los getters de ExchangeRateAPI (líneas 23, 26)"""
    from Exchange import commonExchange as common
    
    api = common.ExchangeRateAPI()
    
    # Test get_api_url (línea 23)
    assert api.get_api_url() == os.environ['EXTERNAL_API_URL']
    
    # Test get_api_key (línea 26) 
    assert api.get_api_key() == os.environ['EXCHANGE_API_ACCESS_KEY']


@patch("boto3.client")
def test_validate_token_and_get_user_success(mock_boto_client):
    """Test para validación exitosa de token"""
    from Exchange import commonExchange as common
    
    # Mock del cliente lambda
    mock_lambda_client = MagicMock()
    mock_boto_client.return_value = mock_lambda_client
    
    # Mock de respuesta exitosa
    mock_response = {
        'Payload': MagicMock()
    }
    mock_response['Payload'].read.return_value = json.dumps({
        'statusCode': 200,
        'body': json.dumps({'user_id': 'user123'})
    }).encode()
    mock_lambda_client.invoke.return_value = mock_response
    
    # Evento con token válido
    event = {
        'headers': {
            'Authorization': 'Bearer valid_token'
        }
    }
    
    user_id = common.validate_token_and_get_user(event)
    assert user_id == 'user123'


@patch("boto3.client")
def test_validate_token_missing_token(mock_boto_client):
    """Test para token faltante (línea 102)"""
    from Exchange import commonExchange as common
    
    # Evento sin token
    event = {
        'headers': {}
    }
    
    # Verificar que se lanza excepción
    with pytest.raises(Exception) as exc_info:
        common.validate_token_and_get_user(event)
    
    assert "Authorization token is missing" in str(exc_info.value)


@patch("boto3.client")
def test_validate_token_invalid_token(mock_boto_client):
    """Test para token inválido (línea 116)"""
    from Exchange import commonExchange as common
    
    # Mock del cliente lambda
    mock_lambda_client = MagicMock()
    mock_boto_client.return_value = mock_lambda_client
    
    # Mock de respuesta con token inválido
    mock_response = {
        'Payload': MagicMock()
    }
    mock_response['Payload'].read.return_value = json.dumps({
        'statusCode': 401,
        'body': json.dumps({'error': 'Invalid token'})
    }).encode()
    mock_lambda_client.invoke.return_value = mock_response
    
    # Evento con token inválido
    event = {
        'headers': {
            'Authorization': 'Bearer invalid_token'
        }
    }
    
    # Verificar que se lanza excepción
    with pytest.raises(Exception) as exc_info:
        common.validate_token_and_get_user(event)
    
    assert "Unauthorized - Invalid or expired token" in str(exc_info.value)


@patch("boto3.client")
def test_validate_token_missing_headers(mock_boto_client):
    """Test para evento sin headers"""
    from Exchange import commonExchange as common
    
    # Evento sin headers
    event = {}
    
    # Verificar que se lanza excepción
    with pytest.raises(Exception) as exc_info:
        common.validate_token_and_get_user(event)
    
    assert "Authorization token is missing" in str(exc_info.value)


def test_get_rate_from_db_not_found(dynamodb_table):
    """Test para cuando no se encuentra una tasa en la DB"""
    from Exchange import commonExchange as common
    
    # Buscar una tasa que no existe
    result = common.get_rate_from_db("USD", "XYZ")
    assert result is None


def test_delete_rates_by_source_empty_result(dynamodb_table):
    """Test para eliminar tasas cuando no hay resultados"""
    from Exchange import commonExchange as common
    
    # Intentar eliminar tasas de una moneda que no existe
    # No debería lanzar excepción
    common.delete_rates_by_source("XYZ")
    
    # Verificar que no pasa nada malo
    assert True  # Si llegamos aquí, no hubo excepción


# Tests adicionales para mejorar la robustez
def test_save_rates_to_db_with_existing_data(dynamodb_table):
    """Test para verificar que se borran las tasas antiguas antes de guardar nuevas"""
    from Exchange import commonExchange as common
    
    timestamp = int(time.time())
    
    # Guardar tasas iniciales para USD
    initial_quotes = {'USDPEN': 3.70, 'USDEUR': 0.85}
    common.save_rates_to_db(initial_quotes, timestamp)
    
    # Verificar que se guardaron
    assert common.get_rate_from_db('USD', 'PEN')['rate'] == '3.7'
    assert common.get_rate_from_db('USD', 'EUR')['rate'] == '0.85'
    
    # Guardar nuevas tasas para USD (debería reemplazar las anteriores)
    new_quotes = {'USDPEN': 3.75, 'USDJPY': 150.0}
    common.save_rates_to_db(new_quotes, timestamp + 100)
    
    # Verificar que se actualizaron correctamente
    assert common.get_rate_from_db('USD', 'PEN')['rate'] == '3.75'
    assert common.get_rate_from_db('USD', 'EUR') is None  # Debería haberse eliminado
    assert common.get_rate_from_db('USD', 'JPY')['rate'] == '150.0'


def test_ttl_and_timestamps(dynamodb_table):
    """Test para verificar que se establecen correctamente TTL y timestamps"""
    from Exchange import commonExchange as common
    
    timestamp = int(time.time())
    rate = '3.75'
    
    # Guardar tasa
    common.save_rate_to_db('USD', 'PEN', rate, timestamp)
    
    # Obtener y verificar campos
    item = common.get_rate_from_db('USD', 'PEN')
    
    assert item['rate'] == rate
    assert item['expiration'] == timestamp
    assert 'fetched_at' in item
    assert 'ttl' in item
    assert item['ttl'] > item['fetched_at']  # TTL debe ser mayor que fetched_at


@patch("urllib.request.urlopen")
def test_api_network_error(mock_urlopen):
    """Test para error de red en la API"""
    from Exchange import commonExchange as common
    
    # Simular error de red
    mock_urlopen.side_effect = Exception("Network error")
    
    api = common.ExchangeRateAPI()
    
    # Verificar que se propaga la excepción
    with pytest.raises(Exception) as exc_info:
        api.fetch_rate_for_pair("USD", "PEN")
    
    assert "Network error" in str(exc_info.value)


def test_dynamodb_connection_getter():
    """Test para el getter de DynamoDBConnection"""
    from Exchange import commonExchange as common
    
    with mock_dynamodb():
        # Crear tabla para que el singleton funcione
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = os.environ["RATES_TABLE"]
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'from', 'KeyType': 'HASH'},
                {'AttributeName': 'to', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'from', 'AttributeType': 'S'},
                {'AttributeName': 'to', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        db_conn = common.DynamoDBConnection()
        table = db_conn.get_table()
        
        assert table is not None
        assert table.table_name == table_name