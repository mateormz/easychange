import os
import json
import pytest
import sys
import importlib
from unittest.mock import patch, MagicMock

# Configura las variables de entorno necesarias
os.environ["VALIDATE_TOKEN_FUNCTION"] = "profile-auth-api"
os.environ["STAGE"] = "dev"

def reload_module_and_reset_singleton():
    # Elimina el módulo y recarga para evitar uso de singleton ya instanciado
    if "Profile.common" in sys.modules:
        del sys.modules["Profile.common"]
    import Profile.common
    importlib.reload(Profile.common)
    return Profile.common

@patch("boto3.client")
def test_validate_token_success(mock_boto_client):
    mock_payload = MagicMock()
    mock_payload.read.return_value = json.dumps({
        "statusCode": 200,
        "body": json.dumps({"user_id": "user123"})
    }).encode()

    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {"Payload": mock_payload}
    mock_boto_client.return_value = mock_lambda

    common = reload_module_and_reset_singleton()
    event = {"headers": {"Authorization": "Bearer token"}}
    user_id = common.validate_token_and_get_user(event)
    assert user_id == "user123"

@patch("boto3.client")
def test_validate_token_missing(mock_boto_client):
    common = reload_module_and_reset_singleton()
    event = {"headers": {}}
    with pytest.raises(Exception) as excinfo:
        common.validate_token_and_get_user(event)
    assert "Authorization token is missing" in str(excinfo.value)

@patch("boto3.client")
def test_validate_token_invalid_response(mock_boto_client):
    mock_payload = MagicMock()
    mock_payload.read.return_value = json.dumps({
        "statusCode": 401,
        "body": "{}"
    }).encode()

    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {"Payload": mock_payload}
    mock_boto_client.return_value = mock_lambda

    common = reload_module_and_reset_singleton()
    event = {"headers": {"Authorization": "Bearer bad-token"}}
    with pytest.raises(Exception) as excinfo:
        common.validate_token_and_get_user(event)
    assert "Unauthorized" in str(excinfo.value)