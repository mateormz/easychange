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

            # Extract bank account ID and transfer amount from the request body
            bank_acc_id = body.get('bankAccId')
            usuario_id = body.get('usuario_id')  # The user ID of the account holder
            transfered_money = body.get('transfered_money')

            if not bank_acc_id or not transfered_money or not usuario_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'bankAccId, usuario_id, and transfered_money are required'})
                }

            # Convert transferred money to Decimal for calculations
            try:
                transfered_money = Decimal(str(transfered_money))
            except Exception:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Invalid amount format'})
                }

            # Fetch the current amount of money in the bank account
            response = table.get_item(
                Key={'usuario_id': usuario_id, 'cuenta_id': bank_acc_id}  # Full key to get account
            )

            if 'Item' not in response:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': 'Bank account not found'})
                }

            current_amount = response['Item'].get('amount', '0')

            # Convert the current amount (stored as a string) to Decimal
            current_amount = Decimal(str(current_amount))

            # Calculate the new amount
            new_amount = current_amount + transfered_money

            # Update the bank account with the new amount
            table.update_item(
                Key={'usuario_id': usuario_id, 'cuenta_id': bank_acc_id},
                UpdateExpression="SET amount = :new_amount",
                ExpressionAttributeValues={':new_amount': str(new_amount)}  # Save as string
            )

            return self.format_response('Amount successfully updated')

        except Exception as e:
            return self.handle_error(e)


def lambda_handler(event, context):
    handler = AddMoneyToBankAccountHandler()
    return handler.perform_action(event)