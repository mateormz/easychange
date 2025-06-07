import boto3
import os
import json

dynamodb = boto3.resource('dynamodb')
table_name = os.environ["TABLE_BANKACC"]
table = dynamodb.Table(table_name)

# Singleton para la lógica de validación del user_id
class UserIdValidator:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_user_id_from_event(self, event):
        user_id = event.get("pathParameters", {}).get("user_id")
        if not user_id:
            raise ValueError("Missing user_id in path parameters")
        return user_id

# Instancia singleton
user_id_validator = UserIdValidator()

def lambda_handler(event, context):
    try:
        # Usar el singleton para validar y extraer el user_id
        user_id = user_id_validator.get_user_id_from_event(event)

        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('usuario_id').eq(user_id)
        )

        return {
            "statusCode": 200,
            "body": json.dumps(response.get("Items", []))
        }

    except ValueError as ve:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(ve)})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
