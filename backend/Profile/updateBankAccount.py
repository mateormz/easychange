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
        raise NotImplementedError("Subclasses should implement this method")


# Subclass that handles the update bank account operation
class UpdateBankAccountHandler(BaseBankAccountHandler):
    def perform_action(self, event):
        try:
            # Prepare data
            user_id, body = self.validate_and_prepare_data(event)
            cuenta_id = event['pathParameters']['cuenta_id']

            if not body:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Request body is missing'})
                }

            # If amount is present, convert it to float for backend processing
            if 'amount' in body:
                try:
                    body['amount'] = str(float(body['amount']))  # Ensure it's a valid float, store as string
                except ValueError:
                    raise Exception("Invalid amount value")

            # Prepare update expression
            update_expression = "SET " + ", ".join(f"#{k} = :{k}" for k in body)
            expression_attribute_names = {f"#{k}": k for k in body}
            expression_attribute_values = {f":{k}": v for k, v in body.items()}

            # Perform the update in DynamoDB
            table.update_item(
                Key={
                    'usuario_id': user_id,
                    'cuenta_id': cuenta_id
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values
            )

            # Return success response
            return self.format_response('Cuenta actualizada exitosamente')

        except Exception as e:
            return self.handle_error(e)


def lambda_handler(event, context):
    # Instantiate the handler and execute the update account action
    handler = UpdateBankAccountHandler()
    return handler.perform_action(event)