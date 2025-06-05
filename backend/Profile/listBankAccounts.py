import boto3
import os
import json
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table_name = os.environ["TABLE_BANKACC"]
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

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
        };
