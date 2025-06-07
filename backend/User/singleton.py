import boto3

class DynamoDBSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            print("[INFO] Creando nueva instancia de DynamoDB")
            cls._instance = super(DynamoDBSingleton, cls).__new__(cls)
            cls._instance.resource = boto3.resource("dynamodb")
        else:
            print("[INFO] Reutilizando instancia de DynamoDB")
        return cls._instance

    def get_resource(self):
        return self.resource


class LambdaClientSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            print("[INFO] Creando nueva instancia de Lambda Client")
            cls._instance = super(LambdaClientSingleton, cls).__new__(cls)
            cls._instance.client = boto3.client("lambda")
        else:
            print("[INFO] Reutilizando instancia de Lambda Client")
        return cls._instance

    def get_client(self):
        return self.client


def get_dynamodb():
    return DynamoDBSingleton().get_resource()

def get_lambda_client():
    return LambdaClientSingleton().get_client()