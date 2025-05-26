import boto3
import os
import json
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
logs_table = dynamodb.Table(os.environ["LOGS_TABLE"])

def lambda_handler(event, context):
    try:
        # Obtener tenant_id de query string o usar default
        tenant_id = event.get('queryStringParameters', {}).get('tenant_id', 'default')

        # Consultar logs ordenados por timestamp descendente
        response = logs_table.query(
            KeyConditionExpression=Key('tenant_id').eq(tenant_id),
            ScanIndexForward=False,
            Limit=50
        )

        logs = [{'timestamp': item['timestamp'], 'message': item['message']} for item in response.get('Items', [])]

        return {
            'statusCode': 200,
            'body': json.dumps({'logs': logs})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
