import pytest
import json
import time
from unittest.mock import MagicMock
from commonExchange import (
    ExchangeRateAPI,
    DynamoDBConnection,
    save_rate_to_db,
    get_rate_from_db,
    delete_rate_from_db,
)

# -------------------------------------
# Fijar variables de entorno necesarias
# -------------------------------------
@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv('EXTERNAL_API_URL', 'https://mockapi.com')
    monkeypatch.setenv('EXCHANGE_API_ACCESS_KEY', 'mockkey')
    monkeypatch.setenv('RATES_TABLE', 'mock-table')
    monkeypatch.setenv('CACHE_TTL_SECONDS', '3600')

# -------------------------------------
# Pruebas de ExchangeRateAPI (mock API externa)
# -------------------------------------
def test_fetch_rate_for_pair_success(mocker):
    mock_urlopen = mocker.patch('urllib.request.urlopen')
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        'success': True,
        'quotes': {'USDJPY': 150.0},
        'timestamp': 1234567890
    }).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    api = ExchangeRateAPI()
    rate, timestamp = api.fetch_rate_for_pair("USD", "JPY")
    assert rate == "150.0"
    assert timestamp == 1234567890

def test_fetch_rates_for_source_success(mocker):
    mock_urlopen = mocker.patch('urllib.request.urlopen')
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        'success': True,
        'quotes': {'USDEUR': 0.91},
        'timestamp': 1234567890
    }).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    api = ExchangeRateAPI()
    quotes, ts = api.fetch_rates_for_source("USD")
    assert 'USDEUR' in quotes
    assert ts == 1234567890

# -------------------------------------
# Pruebas con DynamoDB usando moto
# -------------------------------------
from moto import mock_dynamodb
import boto3

@mock_dynamodb
def setup_dynamodb():
    table_name = 'dev-exchange-rates'
    client = boto3.client('dynamodb', region_name='us-east-1')
    client.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'from', 'KeyType': 'HASH'},
            {'AttributeName': 'to', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'from', 'AttributeType': 'S'},
            {'AttributeName': 'to', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    return boto3.resource('dynamodb').Table(table_name)

@mock_dynamodb
def test_save_and_get_rate_from_db(monkeypatch):
    table = setup_dynamodb()
    monkeypatch.setenv('RATES_TABLE', table.name)

    save_rate_to_db('USD', 'EUR', 0.91, 1234567890)
    item = get_rate_from_db('USD', 'EUR')
    assert item['rate'] == '0.91'

@mock_dynamodb
def test_delete_rate_from_db(monkeypatch):
    table = setup_dynamodb()
    monkeypatch.setenv('RATES_TABLE', table.name)

    save_rate_to_db('USD', 'EUR', 0.91, 1234567890)
    delete_rate_from_db('USD', 'EUR')
    item = get_rate_from_db('USD', 'EUR')
    assert item is None