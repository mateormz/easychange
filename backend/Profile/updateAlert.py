import boto3
import os
import json
from decimal import Decimal
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_ALERTS'])

# Base class for shared logic
class BaseAlertHandler:
    def validate_and_prepare_data(self, event):
        user_id = validate_token_and_get_user(event)
        body = json.loads(event.get('body', '{}'))
        return user_id, body

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

# Subclass for updating an alert
class UpdateAlertHandler(BaseAlertHandler):
    def perform_action(self, event):
        try:
            user_id, body = self.validate_and_prepare_data(event)
            alerta_id = event['pathParameters']['alerta_id']

            if not body:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Request body is missing'})
                }

            # Convert 'umbral' to Decimal if present
            if 'umbral' in body:
                try:
                    body['umbral'] = Decimal(str(body['umbral']))
                except Exception:
                    raise Exception("Invalid 'umbral' value. Must be a number.")

            update_expression = "SET " + ", ".join(f"#{k} = :{k}" for k in body)
            expression_attribute_names = {f"#{k}": k for k in body}
            expression_attribute_values = {f":{k}": v for k, v in body.items()}

            table.update_item(
                Key={
                    'usuario_id': user_id,
                    'alerta_id': alerta_id
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values
            )

            return self.format_response('Alerta actualizada')

        except Exception as e:
            return self.handle_error(e)

def lambda_handler(event, context):
    handler = UpdateAlertHandler()
    return handler.perform_action(event)