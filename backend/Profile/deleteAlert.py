
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

    def format_response(self, message):
        return {
            'statusCode': 200,
            'body': json.dumps({'message': message})
        }

    def perform_action(self, event):
        raise NotImplementedError("Subclasses must implement perform_action()")

# Subclass for deleting an alert
class DeleteAlertHandler(BaseAlertHandler):
    def perform_action(self, event):
        try:
            user_id = self.validate_user(event)
            alerta_id = event['pathParameters']['alerta_id']

            table.delete_item(
                Key={
                    'usuario_id': user_id,
                    'alerta_id': alerta_id
                }
            )

            return self.format_response('Alerta eliminada')

        except Exception as e:
            return self.handle_error(e)

def lambda_handler(event, context):
    handler = DeleteAlertHandler()
    return handler.perform_action(event)
