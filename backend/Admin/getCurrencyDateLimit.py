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

        # Obtener configuración de DynamoDB
        dynamodb = DynamoDBConnection()
        table = dynamodb.get_table(os.environ['EXCHANGE_RATE_TABLE'])
        
        response = table.get_item(Key={'config_id': 'currency_date_limit'})
        
        if 'Item' in response:
            return {
                'statusCode': 200,
                'body': json.dumps(response['Item'])
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Currency date limit not set'})
            }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
