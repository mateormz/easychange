import boto3
import os
import json
import uuid
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["TABLE_REPORTS"])

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)
        body = json.loads(event.get('body', '{}'))

        report_id = str(uuid.uuid4())
        title = body['title']
        content = body.get('content', '')

        item = {
            "usuario_id": user_id,
            "report_id": report_id,
            "title": title,
            "content": content
        }

        table.put_item(Item=item)

        return {
            'statusCode': 201,
            'body': json.dumps({'message': 'Reporte creado con éxito', 'report_id': report_id})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
