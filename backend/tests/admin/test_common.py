import os
import json
import pytest
from unittest.mock import patch, MagicMock

# Establecer variables de entorno requeridas por el módulo
os.environ["SERVICE_NAME"] = "disdb-auth-api"
os.environ["STAGE"] = "dev"
os.environ["VALIDATE_TOKEN_FUNCTION"] = "validateToken"
os.environ["USER_SERVICE_NAME"] = "easychange-auth-api"

from Admin.commonAdmin import DynamoDBConnection, validate_token_and_get_user, get_user_role_by_user_id

class TestDynamoDBConnection:
    def test_dynamodb_connection_singleton_first_instance(self):
        """Test que se crea una nueva instancia la primera vez"""
        # Resetear la instancia singleton
        DynamoDBConnection._instance = None
        
        with patch("boto3.resource") as mock_resource, \
             patch("builtins.print") as mock_print:
            
            mock_dynamodb = MagicMock()
            mock_resource.return_value = mock_dynamodb
            
            instance = DynamoDBConnection()
            
            # Verificar que se creó la instancia
            assert instance is not None
            assert instance.dynamodb == mock_dynamodb
            mock_resource.assert_called_once_with('dynamodb')
            mock_print.assert_called_with("[INFO] Creando nueva instancia de DynamoDB")
    
    def test_dynamodb_connection_singleton_reuse_instance(self):
        """Test que se reutiliza la instancia existente"""
        # Crear primera instancia
        DynamoDBConnection._instance = None
        
        with patch("boto3.resource") as mock_resource, \
             patch("builtins.print") as mock_print:
            
            mock_dynamodb = MagicMock()
            mock_resource.return_value = mock_dynamodb
            
            instance1 = DynamoDBConnection()
            instance2 = DynamoDBConnection()
            
            # Verificar que es la misma instancia
            assert instance1 is instance2
            # boto3.resource solo debe llamarse una vez
            mock_resource.assert_called_once_with('dynamodb')
            # Verificar los prints
            assert mock_print.call_count == 2
            mock_print.assert_any_call("[INFO] Creando nueva instancia de DynamoDB")
            mock_print.assert_any_call("[INFO] Reutilizando la instancia de DynamoDB")
    
    def test_get_table(self):
        """Test del método get_table"""
        # Resetear instancia
        DynamoDBConnection._instance = None
        
        with patch("boto3.resource") as mock_resource:
            mock_dynamodb = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.Table.return_value = mock_table
            mock_resource.return_value = mock_dynamodb
            
            db_conn = DynamoDBConnection()
            result = db_conn.get_table("test_table")
            
            assert result == mock_table
            mock_dynamodb.Table.assert_called_once_with("test_table")

class TestValidateTokenAndGetUser:
    def test_validate_token_and_get_user_success(self):
        """Test caso exitoso"""
        mock_event = {
            "headers": {
                "Authorization": "mocked-token"
            }
        }

        fake_payload = MagicMock()
        fake_payload.read.return_value = json.dumps({
            "statusCode": 200,
            "body": json.dumps({"user_id": "user123"})
        }).encode()

        with patch("boto3.client") as mock_client:
            mock_lambda = MagicMock()
            mock_lambda.invoke.return_value = {"Payload": fake_payload}
            mock_client.return_value = mock_lambda

            user_id, token = validate_token_and_get_user(mock_event)

            assert user_id == "user123"
            assert token == "mocked-token"
            
            # Verificar que se llamó con los parámetros correctos
            mock_lambda.invoke.assert_called_once_with(
                FunctionName="disdb-auth-api-dev-validateToken",
                InvocationType='RequestResponse',
                Payload=json.dumps({"body": json.dumps({"token": "mocked-token"})})
            )

    def test_validate_token_and_get_user_missing_token(self):
        """Test cuando falta el token de autorización"""
        mock_event = {
            "headers": {}
        }

        with pytest.raises(Exception) as excinfo:
            validate_token_and_get_user(mock_event)
        assert "Authorization token is missing" in str(excinfo.value)

    def test_validate_token_and_get_user_missing_headers(self):
        """Test cuando faltan los headers completamente"""
        mock_event = {}

        with pytest.raises(Exception) as excinfo:
            validate_token_and_get_user(mock_event)
        assert "Authorization token is missing" in str(excinfo.value)

    def test_validate_token_and_get_user_invalid_token(self):
        """Test token inválido"""
        mock_event = {
            "headers": {
                "Authorization": "invalid-token"
            }
        }

        fake_payload = MagicMock()
        fake_payload.read.return_value = json.dumps({
            "statusCode": 401
        }).encode()

        with patch("boto3.client") as mock_client:
            mock_lambda = MagicMock()
            mock_lambda.invoke.return_value = {"Payload": fake_payload}
            mock_client.return_value = mock_lambda

            with pytest.raises(Exception) as excinfo:
                validate_token_and_get_user(mock_event)
            assert "Unauthorized - Invalid or expired token" in str(excinfo.value)

    def test_validate_token_and_get_user_empty_body(self):
        """Test cuando el body está vacío - debe fallar con JSONDecodeError"""
        mock_event = {
            "headers": {
                "Authorization": "mocked-token"
            }
        }

        fake_payload = MagicMock()
        fake_payload.read.return_value = json.dumps({
            "statusCode": 200,
            "body": ""
        }).encode()

        with patch("boto3.client") as mock_client:
            mock_lambda = MagicMock()
            mock_lambda.invoke.return_value = {"Payload": fake_payload}
            mock_client.return_value = mock_lambda

            with pytest.raises(json.JSONDecodeError):
                validate_token_and_get_user(mock_event)

    def test_validate_token_and_get_user_none_body(self):
        """Test cuando el body es None - usa default '{}'"""
        mock_event = {
            "headers": {
                "Authorization": "mocked-token"
            }
        }

        fake_payload = MagicMock()
        fake_payload.read.return_value = json.dumps({
            "statusCode": 200
            # Sin 'body' key
        }).encode()

        with patch("boto3.client") as mock_client:
            mock_lambda = MagicMock()
            mock_lambda.invoke.return_value = {"Payload": fake_payload}
            mock_client.return_value = mock_lambda

            user_id, token = validate_token_and_get_user(mock_event)

            assert user_id is None
            assert token == "mocked-token"

    def test_validate_token_and_get_user_missing_user_id(self):
        """Test cuando no hay user_id en la respuesta"""
        mock_event = {
            "headers": {
                "Authorization": "mocked-token"
            }
        }

        fake_payload = MagicMock()
        fake_payload.read.return_value = json.dumps({
            "statusCode": 200,
            "body": json.dumps({"other_field": "value"})
        }).encode()

        with patch("boto3.client") as mock_client:
            mock_lambda = MagicMock()
            mock_lambda.invoke.return_value = {"Payload": fake_payload}
            mock_client.return_value = mock_lambda

            user_id, token = validate_token_and_get_user(mock_event)

            assert user_id is None
            assert token == "mocked-token"

class TestGetUserRoleByUserId:
    def test_get_user_role_by_user_id_success(self):
        """Test caso exitoso"""
        fake_payload = MagicMock()
        fake_payload.read.return_value = json.dumps({
            "statusCode": 200,
            "body": json.dumps({"role": "admin"})
        }).encode()

        with patch("boto3.client") as mock_client:
            mock_lambda = MagicMock()
            mock_lambda.invoke.return_value = {"Payload": fake_payload}
            mock_client.return_value = mock_lambda

            role = get_user_role_by_user_id("user123", "mocked-token")
            assert role == "admin"
            
            # Verificar que se llamó con los parámetros correctos
            expected_payload = {
                'pathParameters': {
                    'user_id': "user123"
                },
                'headers': {
                    'Authorization': "mocked-token"
                }
            }
            mock_lambda.invoke.assert_called_once_with(
                FunctionName="easychange-auth-api-dev-getUserById",
                InvocationType='RequestResponse',
                Payload=json.dumps(expected_payload)
            )

    def test_get_user_role_by_user_id_default_role(self):
        """Test cuando no hay rol, debe devolver 'user' por defecto"""
        fake_payload = MagicMock()
        fake_payload.read.return_value = json.dumps({
            "statusCode": 200,
            "body": json.dumps({"other_field": "value"})
        }).encode()

        with patch("boto3.client") as mock_client:
            mock_lambda = MagicMock()
            mock_lambda.invoke.return_value = {"Payload": fake_payload}
            mock_client.return_value = mock_lambda

            role = get_user_role_by_user_id("user123", "mocked-token")
            assert role == "user"

    def test_get_user_role_by_user_id_not_found(self):
        """Test cuando el usuario no se encuentra"""
        fake_payload = MagicMock()
        fake_payload.read.return_value = json.dumps({
            "statusCode": 404
        }).encode()

        with patch("boto3.client") as mock_client:
            mock_lambda = MagicMock()
            mock_lambda.invoke.return_value = {"Payload": fake_payload}
            mock_client.return_value = mock_lambda

            with pytest.raises(Exception) as excinfo:
                get_user_role_by_user_id("user123", "mocked-token")
            assert "User not found or unable to fetch user info" in str(excinfo.value)

    def test_get_user_role_by_user_id_server_error(self):
        """Test cuando hay error del servidor"""
        fake_payload = MagicMock()
        fake_payload.read.return_value = json.dumps({
            "statusCode": 500
        }).encode()

        with patch("boto3.client") as mock_client:
            mock_lambda = MagicMock()
            mock_lambda.invoke.return_value = {"Payload": fake_payload}
            mock_client.return_value = mock_lambda

            with pytest.raises(Exception) as excinfo:
                get_user_role_by_user_id("user123", "mocked-token")
            assert "User not found or unable to fetch user info" in str(excinfo.value)

    def test_get_user_role_by_user_id_empty_body(self):
        """Test cuando el body está vacío - debe fallar con JSONDecodeError"""
        fake_payload = MagicMock()
        fake_payload.read.return_value = json.dumps({
            "statusCode": 200,
            "body": ""
        }).encode()

        with patch("boto3.client") as mock_client:
            mock_lambda = MagicMock()
            mock_lambda.invoke.return_value = {"Payload": fake_payload}
            mock_client.return_value = mock_lambda

            with pytest.raises(json.JSONDecodeError):
                get_user_role_by_user_id("user123", "mocked-token")

    def test_get_user_role_by_user_id_none_body(self):
        """Test cuando el body es None - debe fallar con TypeError"""
        fake_payload = MagicMock()
        fake_payload.read.return_value = json.dumps({
            "statusCode": 200
            # Sin 'body' key
        }).encode()

        with patch("boto3.client") as mock_client:
            mock_lambda = MagicMock()
            mock_lambda.invoke.return_value = {"Payload": fake_payload}
            mock_client.return_value = mock_lambda

            with pytest.raises(TypeError):
                get_user_role_by_user_id("user123", "mocked-token")

    def test_get_user_role_by_user_id_invalid_json_body(self):
        """Test cuando el body no es JSON válido"""
        fake_payload = MagicMock()
        fake_payload.read.return_value = json.dumps({
            "statusCode": 200,
            "body": "invalid json"
        }).encode()

        with patch("boto3.client") as mock_client:
            mock_lambda = MagicMock()
            mock_lambda.invoke.return_value = {"Payload": fake_payload}
            mock_client.return_value = mock_lambda

            with pytest.raises(json.JSONDecodeError):
                get_user_role_by_user_id("user123", "mocked-token")