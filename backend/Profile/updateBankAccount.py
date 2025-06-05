import boto3
import os
import json

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["TABLE_BANKACC"])

def lambda_handler(event, context):
    try:
        # Obtener user_id desde los parámetros del query string
        user_id = event.get("queryStringParameters", {}).get("user_id")
        if not user_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing user_id in query parameters"})
            }

        cuenta_id = event['pathParameters']['cuenta_id']
        body = json.loads(event.get('body', '{}'))

        if not body:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Request body is missing'})
            }

        # Convertir saldo a string si existe
        if 'saldo' in body:
            body['saldo'] = str(body['saldo'])

        update_expression = "SET " + ", ".join(f"#{k} = :{k}" for k in body)
        expression_attribute_names = {f"#{k}": k for k in body}
        expression_attribute_values = {f":{k}": v for k, v in body.items()}

        # Realizar la actualización en DynamoDB
        table.update_item(
            Key={
                'usuario_id': user_id,
                'cuenta_id': cuenta_id
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Cuenta actualizada exitosamente'})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
