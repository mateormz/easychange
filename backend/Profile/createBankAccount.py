import boto3
import os
import json
import uuid
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["TABLE_BANKACC"])


# Base class with shared logic
class BaseBankAccountHandler:
    def validate_and_prepare_data(self, event):
        # Token validation
        user_id = validate_token_and_get_user(event)
        body = json.loads(event.get('body', '{}'))
        return user_id, body

    def handle_error(self, error):
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(error)})
        }

    def format_response(self, message, cuenta_id):
        return {
            'statusCode': 201,
            'body': json.dumps({'message': message, 'cuenta_id': cuenta_id})
        }

    def perform_action(self, event):
        raise NotImplementedError("Subclasses should implement this method")


# Subclass that handles the create bank account operation
class CreateBankAccountHandler(BaseBankAccountHandler):
    def perform_action(self, event):
        try:
            # Prepare data
            user_id, body = self.validate_and_prepare_data(event)
            cuenta_id = str(uuid.uuid4())
            banco = body['banco']
            moneda = body['moneda']
            numero_cuenta = body['numero_cuenta']
            tipo_cuenta = body['tipo_cuenta']
            alias = body.get('alias', '')
            amount = str(body.get('amount', '0.0'))  # Added amount as a string

            # Convert amount to float for backend operations
            try:
                amount_float = float(amount)
            except ValueError:
                raise Exception("Invalid amount value")

            # Prepare item for DynamoDB
            item = {
                "usuario_id": user_id,
                "cuenta_id": cuenta_id,
                "banco": banco,
                "moneda": moneda,
                "numero_cuenta": numero_cuenta,
                "tipo_cuenta": tipo_cuenta,
                "alias": alias,
                "amount": amount  # Store as string in DynamoDB
            }

            # Store the item in DynamoDB
            table.put_item(Item=item)

            # Return success response
            return self.format_response('Cuenta registrada con éxito', cuenta_id)

        except Exception as e:
            return self.handle_error(e)


def lambda_handler(event, context):
    # Instantiate the handler and execute the create account action
    handler = CreateBankAccountHandler()
    return handler.perform_action(event)
