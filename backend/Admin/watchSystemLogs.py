import json

def lambda_handler(event, context):
    try:
        logs = [
            "2025-05-25 12:00:00 - Sistema iniciado",
            "2025-05-25 12:05:23 - Configuración de franjas horarias actualizada",
            "2025-05-25 12:10:45 - Límites de transacción establecidos",
            "2025-05-25 12:15:00 - Usuario admin autenticado"
        ]

        return {
            'statusCode': 200,
            'body': json.dumps({'logs': logs})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    