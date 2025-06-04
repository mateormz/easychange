import boto3
import json
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['USER_CONVERSIONS_TABLE'])

def lambda_handler(event, context):
    try:
        # Validar token y obtener user_id
        user_id = validate_token_and_get_user(event)

        # Consultar las conversiones de divisas asociadas con el usuario
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
        )

        transactions = response.get('Items', [])

        return {
            'statusCode': 200,
            'body': json.dumps({'transactions': transactions})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
