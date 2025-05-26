import boto3
import os
import json
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["TABLE_REPORTS"])

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)
        report_id = event['pathParameters']['report_id']

        table.delete_item(
            Key={
                'usuario_id': user_id,
                'report_id': report_id
            }
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Reporte eliminado exitosamente'})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
