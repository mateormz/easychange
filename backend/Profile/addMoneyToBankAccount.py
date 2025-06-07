import boto3
import os
import json
from decimal import Decimal
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_BANKACC'])


# Base class for shared logic
class BaseBankAccountHandler:
    def validate_and_prepare_data(self, event):
        user_id = validate_token_and_get_user(event)  # Validate token and extract user info
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


# Subclass for adding money to a bank account
class AddMoneyToBankAccountHandler(BaseBankAccountHandler):
    def perform_action(self, event):
        try:
            # Validate token and extract request data
            user_id, body = self.validate_and_prepare_data(event)

            # Extract bank account ID and amount from the request body
            bank_acc_id = body.get('bankAccId')
            usuario_id = body.get('usuario_id')  # The user ID of the account holder
            amount = body.get('amount')

            if not bank_acc_id or not amount or not usuario_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'bankAccId, usuario_id, and amount are required'})
                }

            # Convert amount to Decimal for calculations
            try:
                amount = Decimal(str(amount))
            except Exception:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Invalid amount format'})
                }

            # Fetch the current saldo of the bank account
            response = table.get_item(
                Key={'usuario_id': usuario_id, 'cuenta_id': bank_acc_id}
            )

            if 'Item' not in response:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': 'Bank account not found'})
                }

            current_saldo = response['Item'].get('saldo', '0')

            # Convert the current saldo (stored as a string) to Decimal
            current_saldo = Decimal(str(current_saldo))

            # Calculate the new saldo
            new_saldo = current_saldo + amount

            # Update the bank account with the new saldo
            table.update_item(
                Key={'usuario_id': usuario_id, 'cuenta_id': bank_acc_id},
                UpdateExpression="SET saldo = :new_saldo",
                ExpressionAttributeValues={':new_saldo': str(new_saldo)}  # Save as string
            )

            return self.format_response('Saldo actualizado correctamente')

        except Exception as e:
            return self.handle_error(e)


def lambda_handler(event, context):
    handler = AddMoneyToBankAccountHandler()
    return handler.perform_action(event)
