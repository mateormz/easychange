import boto3

_dynamodb_resource = None
_lambda_client = None

def get_dynamodb():
    global _dynamodb_resource
    if _dynamodb_resource is None:
        print("[INFO] Creando nueva instancia de DynamoDB")
        _dynamodb_resource = boto3.resource("dynamodb")
    else:
        print("[INFO] Reutilizando instancia de DynamoDB")
    return _dynamodb_resource

def get_lambda_client():
    global _lambda_client
    if _lambda_client is None:
        print("[INFO] Creando nueva instancia de Lambda client")
        _lambda_client = boto3.client("lambda")
    else:
        print("[INFO] Reutilizando instancia de Lambda client")
    return _lambda_client