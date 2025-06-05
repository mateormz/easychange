import boto3
import os
import json

class TokenValidator:
    _instance = None
    _lambda_client = None
    
    def __new__(cls):
        if cls._instance is None:
            # Ensure that only one instance is created
            cls._instance = super().__new__(cls)
            cls._lambda_client = boto3.client('lambda')
        return cls._instance

    def validate_token_and_get_user(self, event):
        token = event.get('headers', {}).get('Authorization')
        if not token:
            raise Exception("Authorization token is missing")

        validate_function_name = f"{os.environ['VALIDATE_TOKEN_FUNCTION']}-{os.environ['STAGE']}-validateToken"

        payload = {"body": json.dumps({"token": token})}
        response = self._lambda_client.invoke(
            FunctionName=validate_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        validation_result = json.loads(response['Payload'].read())

        if validation_result.get('statusCode') != 200:
            raise Exception("Unauthorized - Invalid or expired token")

        user_info = json.loads(validation_result.get('body', '{}'))
        return user_info.get('user_id')

# Singleton instance
token_validator = TokenValidator()

def validate_token_and_get_user(event):
    return token_validator.validate_token_and_get_user(event)
