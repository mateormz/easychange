import json
import os
import pytest
from unittest.mock import patch

@patch.dict(os.environ, {
    "STAGE": "dev",
    "SERVICE_NAME": "disdb-auth-api",
    "VALIDATE_TOKEN_FUNCTION": "validateToken",
    "EXCHANGE_SERVICE_NAME": "exchange-rate-api",
    "PROFILE_SERVICE_NAME": "easychange-profile-api",
    "ADMIN_SERVICE_NAME": "easychange-admin-api"
})
@patch("Currency.common.LambdaClientSingleton.get_client")
def test_all_common_functions(mock_get_client):
    from Currency import common

    class DummyPayload:
        def __init__(self, value):
            self.value = value
        def read(self):
            return json.dumps(self.value).encode()

    mock_lambda = mock_get_client.return_value

    # ===================== validate_token_and_get_user =====================
    
    # validate_token_and_get_user (correcto)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": json.dumps({"user_id": "user123"})
        })
    }
    user_id = common.validate_token_and_get_user({"headers": {"Authorization": "Bearer token"}})
    assert user_id == "user123"

    # validate_token_and_get_user (error en lambda)
    mock_lambda.invoke.side_effect = Exception("Lambda error")
    result = common.validate_token_and_get_user({"headers": {"Authorization": "Bearer token"}})
    assert result["statusCode"] == 500
    mock_lambda.invoke.side_effect = None

    # validate_token_and_get_user (token ausente)
    result = common.validate_token_and_get_user({"headers": {}})
    assert result["statusCode"] == 400

    # validate_token_and_get_user (headers ausentes)
    result = common.validate_token_and_get_user({})
    assert result["statusCode"] == 400

    # validate_token_and_get_user (statusCode != 200 desde validación)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 401,
            "body": json.dumps({"error": "Invalid token"})
        })
    }
    result = common.validate_token_and_get_user({"headers": {"Authorization": "Bearer invalid"}})
    assert result["statusCode"] == 401

    # validate_token_and_get_user (body vacío en respuesta exitosa)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": json.dumps({})
        })
    }
    result = common.validate_token_and_get_user({"headers": {"Authorization": "Bearer token"}})
    assert result is None

    # ===================== fetch_rate_for_pair_from_exchange =====================
    
    # fetch_rate_for_pair_from_exchange (tasa OK)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": json.dumps({"rate": 3.75})
        })
    }
    assert common.fetch_rate_for_pair_from_exchange("USD", "PEN", "token") == "3.75"

    # fetch_rate_for_pair_from_exchange (statusCode != 200)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 500,
            "body": "Error externo"
        })
    }
    with pytest.raises(Exception, match="Error al obtener la tasa de cambio"):
        common.fetch_rate_for_pair_from_exchange("USD", "PEN", "token")

    # fetch_rate_for_pair_from_exchange (sin 'rate')
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": json.dumps({})
        })
    }
    with pytest.raises(Exception, match="Tasa de cambio no encontrada"):
        common.fetch_rate_for_pair_from_exchange("USD", "PEN", "token")

    # fetch_rate_for_pair_from_exchange (error en invoke)
    mock_lambda.invoke.side_effect = Exception("Network error")
    with pytest.raises(Exception, match="Failed to fetch exchange rate via Lambda"):
        common.fetch_rate_for_pair_from_exchange("USD", "PEN", "token")
    mock_lambda.invoke.side_effect = None

    # ===================== get_account_balance_from_profile =====================
    
    # get_account_balance_from_profile (correcto)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": json.dumps([{"cuenta_id": "acc001", "amount": "150.0"}])
        })
    }
    assert common.get_account_balance_from_profile("user123", "acc001", "token") == 150.0

    # get_account_balance_from_profile (no user_id)
    with pytest.raises(Exception, match="Missing user_id or account_id"):
        common.get_account_balance_from_profile(None, "acc001", "token")

    # get_account_balance_from_profile (no account_id)
    with pytest.raises(Exception, match="Missing user_id or account_id"):
        common.get_account_balance_from_profile("user123", None, "token")

    # get_account_balance_from_profile (cuenta no encontrada)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": json.dumps([{"cuenta_id": "otra", "amount": "100"}])
        })
    }
    with pytest.raises(Exception, match="Account with account_id acc001 not found"):
        common.get_account_balance_from_profile("user123", "acc001", "token")

    # get_account_balance_from_profile (no body en respuesta)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200
        })
    }
    with pytest.raises(Exception, match="No body found in response"):
        common.get_account_balance_from_profile("user123", "acc001", "token")

    # get_account_balance_from_profile (body como string JSON válido)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": json.dumps({"cuenta_id": "acc001", "amount": "200.0"})
        })
    }
    assert common.get_account_balance_from_profile("user123", "acc001", "token") == 200.0

    # get_account_balance_from_profile (body como string JSON inválido)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": "invalid json"
        })
    }
    with pytest.raises(Exception, match="La respuesta en 'body' no es un JSON válido"):
        common.get_account_balance_from_profile("user123", "acc001", "token")

    # get_account_balance_from_profile (body no es ni lista ni dict) - CORREGIDO
    # Este caso nunca llega a "Expected a list of accounts" porque primero falla en JSON decode
    # Cambiamos el mock para que pase el JSON decode pero falle en el tipo
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": json.dumps("some string")  # JSON válido pero contenido es string
        })
    }
    with pytest.raises(Exception, match="Expected a list of accounts"):
        common.get_account_balance_from_profile("user123", "acc001", "token")

    # get_account_balance_from_profile (lista vacía)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": json.dumps([])
        })
    }
    with pytest.raises(Exception, match="No accounts found for the user"):
        common.get_account_balance_from_profile("user123", "acc001", "token")

    # get_account_balance_from_profile (cuenta sin amount)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": json.dumps([{"cuenta_id": "acc001"}])
        })
    }
    assert common.get_account_balance_from_profile("user123", "acc001", "token") == 0.0

    # get_account_balance_from_profile (error en invoke)
    mock_lambda.invoke.side_effect = Exception("Lambda invoke error")
    with pytest.raises(Exception, match="Error fetching account balance"):
        common.get_account_balance_from_profile("user123", "acc001", "token")
    mock_lambda.invoke.side_effect = None

    # ===================== update_balance_in_profile =====================
    
    # update_balance_in_profile (correcto)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": json.dumps({"ok": True})
        })
    }
    result = common.update_balance_in_profile("acc001", 100.0, "token")
    assert result["statusCode"] == 200

    # update_balance_in_profile (error en invoke)
    mock_lambda.invoke.side_effect = Exception("Update error")
    with pytest.raises(Exception, match="Error al actualizar el monto de la cuenta"):
        common.update_balance_in_profile("acc001", 100.0, "token")
    mock_lambda.invoke.side_effect = None

    # ===================== add_money_to_account_in_profile =====================
    
    # add_money_to_account_in_profile (correcto)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": json.dumps({"ok": True})
        })
    }
    result = common.add_money_to_account_in_profile("acc001", "user123", 50.0, "token")
    assert result["statusCode"] == 200

    # add_money_to_account_in_profile (error en invoke)
    mock_lambda.invoke.side_effect = Exception("Add money error")
    with pytest.raises(Exception, match="Error al agregar dinero a la cuenta destino"):
        common.add_money_to_account_in_profile("acc001", "user123", 50.0, "token")
    mock_lambda.invoke.side_effect = None

    # ===================== call_get_currency_date_limit =====================
    
    # call_get_currency_date_limit (correcto)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": json.dumps({"limit": "2024-12-31"})
        })
    }
    result = common.call_get_currency_date_limit("token")
    assert result["limit"] == "2024-12-31"

    # call_get_currency_date_limit (status distinto de 200)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 500,
            "body": "Some error"
        })
    }
    with pytest.raises(Exception, match="Error al obtener currency date limit"):
        common.call_get_currency_date_limit("token")

    # ===================== call_get_currency_limit =====================
    
    # call_get_currency_limit (status 200)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 200,
            "body": json.dumps({"max": 1000.0})
        })
    }
    result = common.call_get_currency_limit("token")
    assert result["max"] == 1000.0

    # call_get_currency_limit (status distinto de 200)
    mock_lambda.invoke.return_value = {
        "Payload": DummyPayload({
            "statusCode": 500,
            "body": "Internal error"
        })
    }
    with pytest.raises(Exception, match="Error al obtener currency limit"):
        common.call_get_currency_limit("token")


# Test para el Singleton
@patch("Currency.common.boto3.client")
def test_lambda_client_singleton(mock_boto3_client):
    from Currency.common import LambdaClientSingleton
    
    # Reset singleton
    LambdaClientSingleton._client = None
    
    # Primera llamada debe crear el cliente
    mock_boto3_client.return_value = "mocked_client"
    client1 = LambdaClientSingleton.get_client()
    assert client1 == "mocked_client"
    mock_boto3_client.assert_called_once_with('lambda')
    
    # Segunda llamada debe retornar el mismo cliente
    mock_boto3_client.reset_mock()
    client2 = LambdaClientSingleton.get_client()
    assert client2 == "mocked_client"
    assert client1 is client2
    mock_boto3_client.assert_not_called()  # No debe llamar boto3.client nuevamente


# Test para verificar las variables de entorno - CORREGIDO
@patch.dict(os.environ, {
    "EXCHANGE_SERVICE_NAME": "test-exchange",
    "PROFILE_SERVICE_NAME": "test-profile"
})
def test_environment_variables():
    # Recargar el módulo para que tome las nuevas variables de entorno
    import importlib
    from Currency import common
    importlib.reload(common)
    
    # Verificar que las variables se asignan correctamente
    assert common.EXCHANGE_SERVICE_NAME == "test-exchange"
    assert common.PROFILE_SERVICE_NAME == "test-profile"