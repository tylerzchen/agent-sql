import json
import logging
from mangum import Mangum
from adapter import app

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create a Lambda entry point for the FastAPI app (HTTP adapter for MCP server)
handler = Mangum(app)

# Lambda handler for the FastAPI app (HTTP adapter for MCP server)
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

