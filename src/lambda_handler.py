import json
import logging
from mangum import Mangum
from adapter import app

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = Mangum(app)

def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        response = handler(event, context)
        logger.info(f"Event response: {json.dumps(response)}")
        return response
    except Exception as error:
        logger.error(f"Error in lambda handler: {str(error)}")
        return {
            'statusCode': 500, 
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(error)
            })
        }

