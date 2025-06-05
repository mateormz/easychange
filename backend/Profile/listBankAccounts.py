import boto3
import os
import json

dynamodb = boto3.resource('dynamodb')
table_name = os.environ["TABLE_BANKACC"]
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    try:
        # Obtener el user_id desde los parámetros del query string
        user_id = event.get("queryStringParameters", {}).get("user_id")
        if not user_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing user_id in query parameters"})
            }

        # Consultar DynamoDB
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('usuario_id').eq(user_id)
        )

        return {
            "statusCode": 200,
            "body": json.dumps(response.get("Items", []))
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
