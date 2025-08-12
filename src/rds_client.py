import os
import json
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class RDSClient:
    def __init__(self, cluster_arn: str, secret_arn: str, db_name: str = "postgres", region: str = "us-east-1"):
        self.cluster_arn = cluster_arn
        self.secret_arn = secret_arn
        self.db_name = db_name
        self.region = region
        self.rds_client = boto3.client('rds-data', region_name=region)
    
    def execute_query(self, sql_query: str) -> Dict[str, Any]:
        try:
            response = self.rds_client.execute_statement(
                resourceArn=self.cluster_arn,
                secretArn=self.secret_arn,
                database=self.db_name,
                sql=sql_query,
                formatRecordsAs='JSON'
            )
            formatted_records = response.get('formattedRecords', [])
            try:
                parsed_data = json.loads(formatted_records)
            except json.JSONDecodeError as error:
                logger.error(f"Failed to parse JSON: {error}")
                parsed_data = []

            return {
                "success": True,
                "data": parsed_data,
                "row_count": len(parsed_data),
                "columns": list(parsed_data[0].keys()) if parsed_data else [],
                "sql_query": sql_query
            }
        except ClientError as error:
            error_code = error.response['Error']['Code']
            error_message = error.response['Error']['Message']
            logger.error(f"RDS data API error: {error_code} - {error_message}")
            
            return {
                "success": False,
                "error": f"Database error: {error_message}",
                "error_code": error_code,
            }
        except Exception as error:
            logger.error(f"Error executing query: {str(error)}")
            
            return {
                "success": False,
                "error": f"Unknown error: {str(error)}"
            }
    
    def test_connection(self) -> tuple[bool, str]:
        try:
            test_query = "SELECT 1 as test"
            response = self.rds_client.execute_statement(
                resourceArn=self.cluster_arn,
                secretArn=self.secret_arn,
                database=self.db_name,
                sql=test_query
            )
            logger.info(f"Connection successful. {response}")
            return True, None
        except ClientError as error:
            error_code = error.response['Error']['Code']
            error_message = error.response['Error']['Message']
            logger.error(f"RDS data API error: {error_code} - {error_message}")
            return False, f"Error connecting: {error_code} - {error_message}"
        except Exception as error:
            logger.error(f"Error connecting to RDS: {str(error)}")
            return False, f"Error connecting: {str(error)}"