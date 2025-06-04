import json
import os
from commonAdmin import DynamoDBConnection, validate_token_and_get_user, get_user_role_by_user_id

def lambda_handler(event, context):
    try:
        # Validar el token y obtener el user_id y token
        user_id, token = validate_token_and_get_user(event)
        
        # Verificar el rol del usuario
        user_role = get_user_role_by_user_id(user_id, token)
        
        if user_role != 'admin':
            return {
                'statusCode': 403,
                'body': json.dumps({'error': 'Unauthorized - Admin rights are required'})
            }

        # Obtener el monto y el tipo de moneda del body
        body = json.loads(event['body'])
        amount = body.get('amount')
        currency_type = body.get('currency_type', 'USD')  # Default to USD if not provided
        
        if not amount:
            raise ValueError("Amount is required")

        # Guardar en DynamoDB
        dynamodb = DynamoDBConnection()
        table = dynamodb.get_table(os.environ['EXCHANGE_RATE_TABLE'])
        
        # Verificar si ya existe una configuración, y si es así, actualizarla
        response = table.get_item(Key={'config_id': 'currency_limit'})
        
        if 'Item' in response:
            table.update_item(
                Key={'config_id': 'currency_limit'},
                UpdateExpression="SET amount = :amount, currency_type = :currency_type, user_id = :user_id",
                ExpressionAttributeValues={
                    ':amount': amount,
                    ':currency_type': currency_type,
                    ':user_id': user_id
                }
            )
        else:
            table.put_item(Item={
                'config_id': 'currency_limit',
                'amount': amount,
                'currency_type': currency_type,
                'user_id': user_id
            })
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Currency limit set successfully'})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
