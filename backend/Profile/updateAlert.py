import boto3
import os
import json
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_ALERTS'])

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)
        alerta_id = event['pathParameters']['alerta_id']
        body = json.loads(event.get('body', '{}'))

        if not body:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Request body is missing'})
            }

        update_expression = "SET " + ", ".join(f"#{k} = :{k}" for k in body)
        expression_attribute_names = {f"#{k}": k for k in body}
        expression_attribute_values = {f":{k}": v for k, v in body.items()}

        table.update_item(
            Key={
                'usuario_id': user_id,
                'alerta_id': alerta_id
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Alerta actualizada'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
