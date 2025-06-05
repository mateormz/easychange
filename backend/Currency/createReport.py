import boto3
import json
import uuid
import os
from datetime import datetime
from common import validate_token_and_get_user

dynamodb = boto3.resource('dynamodb')
conversions_table = dynamodb.Table(os.environ['USER_CONVERSIONS_TABLE'])
reports_table = dynamodb.Table(os.environ['USER_REPORTS_TABLE'])

def lambda_handler(event, context):
    try:
        user_id = validate_token_and_get_user(event)

        body = json.loads(event.get('body', '{}'))
        start_date_str = body.get('startDate')
        end_date_str = body.get('endDate')

        if not start_date_str or not end_date_str:
            return respond(400, {'error': 'startDate and endDate are required'})

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            return respond(400, {'error': 'Invalid date format. Use YYYY-MM-DD'})

        response = conversions_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
        )

        transactions = response.get('Items', [])
        filtered = [
            txn for txn in transactions
            if start_date <= datetime.strptime(txn['timestamp'], '%Y-%m-%dT%H:%M:%S') <= end_date
        ]

        report_id = str(uuid.uuid4())
        report_data = {
            'report_id': report_id,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'transactions': filtered
        }

        reports_table.put_item(Item=report_data)

        return respond(201, {'reportId': report_id, 'reportData': report_data})

    except Exception as e:
        return respond(500, {'error': str(e)})


def respond(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }
