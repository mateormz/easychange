import boto3
import os
import json
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table_name = os.environ["TABLE_BANKACC"]
table = dynamodb.Table(table_name)

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
    
    def format_response(self, items):
        return {
            'statusCode': 200,
            'body': json.dumps(items)
        }

    def perform_action(self, event):
        raise NotImplementedError("Subclasses should implement this method")

# Subclass that handles the list bank accounts operation
class ListBankAccountsHandler(BaseBankAccountHandler):
    def perform_action(self, event):
        try:
            # Prepare data
            user_id = self.validate_and_prepare_data(event)

            # Query DynamoDB for the bank accounts
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('usuario_id').eq(user_id)
            )

            # Return the formatted response
            return self.format_response(response.get("Items", []))
        
        except Exception as e:
            return self.handle_error(e)

def lambda_handler(event, context):
    # Instantiate the handler and execute the list accounts action
    handler = ListBankAccountsHandler()
    return handler.perform_action(event)
