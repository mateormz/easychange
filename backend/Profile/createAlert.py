
import boto3
import os
import json
import uuid
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

    def format_response(self, message, alerta_id=None):
        body = {'message': message}
        if alerta_id:
            body['alerta_id'] = alerta_id
        return {
            'statusCode': 201,
            'body': json.dumps(body)
        }

    def perform_action(self, event):
        raise NotImplementedError("Subclasses must implement perform_action()")

# Subclass for creating an alert
class CreateAlertHandler(BaseAlertHandler):
    def perform_action(self, event):
        try:
            user_id, body = self.validate_and_prepare_data(event)

            alerta_id = str(uuid.uuid4())
            tipo_cambio = body['tipo_cambio']
            umbral = Decimal(str(body['umbral']))
            direccion = body['direccion']

            item = {
                "usuario_id": user_id,
                "alerta_id": alerta_id,
                "tipo_cambio": tipo_cambio,
                "umbral": umbral,
                "direccion": direccion
            }

            table.put_item(Item=item)

            return self.format_response("Alerta creada", alerta_id)

        except Exception as e:
            return self.handle_error(e)

def lambda_handler(event, context):
    handler = CreateAlertHandler()
    return handler.perform_action(event)
