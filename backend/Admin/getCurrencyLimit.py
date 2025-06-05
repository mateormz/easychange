import json
import os
from commonAdmin import DynamoDBConnection

def lambda_handler(event, context):
    try:
        # Obtener configuración de DynamoDB
        dynamodb = DynamoDBConnection()
        table = dynamodb.get_table(os.environ['EXCHANGE_RATE_TABLE'])
        
        response = table.get_item(Key={'config_id': 'currency_limit'})
        
        if 'Item' in response:
            return {
                'statusCode': 200,
                'body': json.dumps(response['Item'])
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Currency limit not set'})
            }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
