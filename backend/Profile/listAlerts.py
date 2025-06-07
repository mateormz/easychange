import boto3
import os
import json
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_ALERTS'])

# Base class for shared logic
class BaseAlertHandler:
    def validate_user(self, event):
        return validate_token_and_get_user(event)

    def handle_error(self, error):
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(error)})
        }

    def format_response(self, data):
        return {
            'statusCode': 200,
            'body': json.dumps(data, default=str)
        }

    def perform_action(self, event):
        raise NotImplementedError("Subclasses must implement perform_action()")

# Subclass for listing alerts
class ListAlertsHandler(BaseAlertHandler):
    def perform_action(self, event):
        try:
            user_id = self.validate_user(event)

            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('usuario_id').eq(user_id)
            )

            return self.format_response(response.get("Items", []))

        except Exception as e:
            return self.handle_error(e)

def lambda_handler(event, context):
    handler = ListAlertsHandler()
    return handler.perform_action(event)
