import boto3
import os
import json
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["TABLE_BANKACC"])


# Base class with shared logic for CRUD operations
class BaseBankAccountHandler:
    def validate_and_prepare_data(self, event):
        # Token validation
        user_id = validate_token_and_get_user(event)
        return user_id

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
        raise NotImplementedError("Subclasses should implement this method")


# Subclass that handles the delete bank account operation
class DeleteBankAccountHandler(BaseBankAccountHandler):
    def perform_action(self, event):
        try:
            # Prepare data
            user_id = self.validate_and_prepare_data(event)
            cuenta_id = event['pathParameters']['cuenta_id']

            # Delete the bank account from DynamoDB
            table.delete_item(
                Key={
                    'usuario_id': user_id,
                    'cuenta_id': cuenta_id
                }
            )

            # Return success response
            return self.format_response('Cuenta eliminada exitosamente')

        except Exception as e:
            return self.handle_error(e)


def lambda_handler(event, context):
    # Instantiate the handler and execute the delete account action
    handler = DeleteBankAccountHandler()
    return handler.perform_action(event)
