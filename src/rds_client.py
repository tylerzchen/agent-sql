import os
import json
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

CLUSTER_ARN = os.getenv("AURORA_CLUSTER_ARN")
SECRET_ARN = os.getenv("AURORA_SECRET_ARN")
DB_NAME = os.getenv("DATABASE_NAME")

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
            parsed_records = self.parse_records(formatted_records)
            columns = []
            if parsed_records:
                columns = list(parsed_records[0].keys())

            return {
                "success": True,
                "data": parsed_records,
                "row_count": len(parsed_records),
                "columns": columns,
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

    def parse_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_records = []
        for record in records:
            try:
                parsed_record = json.loads(record)
                parsed_records.append(parsed_record)
            except json.JSONDecodeError as error:
                logger.warning(f"Failed to parse record: {error}")
                parsed_records.append({ "raw_data": record })
        
        return parsed_records
    
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

def main():
    rds_client = RDSClient(
        cluster_arn=CLUSTER_ARN,
        secret_arn=SECRET_ARN,
        db_name=DB_NAME,
        region="us-east-1"
    )
    success, error = rds_client.test_connection()
    if success:
        logger.info("Connection successful")
        sample_query = ""
        result = rds_client.execute_query(sample_query)
        if result["success"]:
            logger.info(f"Query successful. {result}")
        else:
            logger.error(f"Query failed: {result['error']}")
    else:
        logger.error(f"Connection failed: {error}")

if __name__ == "__main__":
    main()