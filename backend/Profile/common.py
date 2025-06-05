
# common.py
import boto3
import os
import json

def validate_token_and_get_user(event):
    token = event.get('headers', {}).get('Authorization')
    if not token:
        raise Exception("Authorization token is missing")

    lambda_client = boto3.client('lambda')
    validate_function_name = f"{os.environ['VALIDATE_TOKEN_FUNCTION']}-{os.environ['STAGE']}-validateToken"

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
