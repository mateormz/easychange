import boto3
import os
import json
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
config_table = dynamodb.Table(os.environ["CONFIG_TABLE"])
logs_table = dynamodb.Table(os.environ["LOGS_TABLE"])

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        tenant_id = body.get('tenant_id')
        transaction_limit = body.get('transaction_limit')

        if not tenant_id or transaction_limit is None:
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'tenant_id y transaction_limit son requeridos'})
            }

        config_table.put_item(Item={
            'tenant_id': tenant_id,
            'config_id': 'transaction-limit',
            'value': transaction_limit
        })

        # Insertar log con fecha y mensaje
        logs_table.put_item(Item={
            'tenant_id': tenant_id,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'Límite de transacción configurado a: {transaction_limit}'
        })

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Límite de transacción configurado correctamente'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
