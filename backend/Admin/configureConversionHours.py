import boto3
import os
import json

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["CONFIG_TABLE"])

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        tenant_id = body.get('tenant_id')
        conversion_hours = body.get('conversion_hours')

        if not tenant_id or not conversion_hours:
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'tenant_id y conversion_hours son requeridos'})
            }

        table.put_item(Item={
            'tenant_id': tenant_id,
            'config_id': 'conversion-hours',
            'value': conversion_hours
        })

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Franjas horarias configuradas correctamente'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
