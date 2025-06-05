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

        # Obtener la fecha del body
        body = json.loads(event['body'])
        date_limit = body.get('date_limit')
        
        if not date_limit:
            raise ValueError("Date limit is required")
        
        # Guardar en DynamoDB
        dynamodb = DynamoDBConnection()
        table = dynamodb.get_table(os.environ['EXCHANGE_RATE_TABLE'])
        
        # Verificar si ya existe una configuración, y si es así, actualizarla
        response = table.get_item(Key={'config_id': 'currency_date_limit'})
        
        if 'Item' in response:
            table.update_item(
                Key={'config_id': 'currency_date_limit'},
                UpdateExpression="SET date_limit = :date_limit, user_id = :user_id",
                ExpressionAttributeValues={
                    ':date_limit': date_limit,
                    ':user_id': user_id
                }
            )
        else:
            table.put_item(Item={
                'config_id': 'currency_date_limit',
                'date_limit': date_limit,
                'user_id': user_id
            })
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Currency date limit set successfully'})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
