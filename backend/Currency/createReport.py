import boto3
import json
from datetime import datetime
import uuid

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['USER_CONVERSIONS_TABLE'])


def lambda_handler(event, context):
    try:
        # Validar token y obtener user_id
        user_id = validate_token_and_get_user(event)

        # Extraer las fechas de inicio y fin del rango del body
        body = json.loads(event.get('body', '{}'))
        start_date = body.get('startDate')
        end_date = body.get('endDate')

        if not start_date or not end_date:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'startDate and endDate are required'})
            }

        # Convertir las fechas en formato datetime
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Consultar las conversiones dentro del rango de fechas
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
        )

        transactions = response.get('Items', [])
        filtered_transactions = [
            txn for txn in transactions if
            start_date <= datetime.strptime(txn['timestamp'], '%Y-%m-%dT%H:%M:%S') <= end_date
        ]

        # Crear un reporte con las conversiones filtradas
        report_id = str(uuid.uuid4())
        report_data = {
            'report_id': report_id,
            'user_id': user_id,
            'transactions': filtered_transactions,
        }

        # Guardar el reporte en DynamoDB
        report_table = dynamodb.Table(os.environ['USER_REPORTS_TABLE'])
        report_table.put_item(Item=report_data)

        return {
            'statusCode': 201,
            'body': json.dumps({'reportId': report_id, 'reportData': report_data})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
