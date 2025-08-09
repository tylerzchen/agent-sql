import logging
import json
import re
import boto3
import time
from botocore.exceptions import ClientError
import sqlparse
from sqlparse.tokens import Keyword

from prompt import create_system_prompt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# TODO: Add provisioning throughput so Claude Sonnet 4 works
# TODO: Add error handling, if invalid SQL, run the model again with an error prompt
class SQLAgent:
    def __init__(self, model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0", region: str = "us-east-1"):
        self.model_id = model_id
        self.region = region
        self.bedrock_agent = boto3.client(service_name='bedrock-runtime', region_name=region)
        self.last_request_time = 0
        self.min_request_interval = 5.0
        
    def generate_sql(self, user_query: str) -> tuple[str, str]:
        current_time = time.time()
        if current_time - self.last_request_time < self.min_request.interval:
            time.sleep(self.min_request_interval)
        self.last_request_time = time.time()
        
        system_prompt = create_system_prompt(user_query=user_query)
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "temperature": 0.1,
            "max_tokens": 3000,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": system_prompt}],
                }
            ],
        })

        try:
            response = self.bedrock_agent.invoke_model(
                modelId=self.model_id,
                body=body
            )
        except (ClientError, Exception) as error:
            logger.error(f"ERROR: Can't invoke '{self.model_id}'. Reason: {error}")
            return

        decoded_response = json.loads(response["body"].read())
        text_response = decoded_response["content"][0]["text"]

        if '<sql_statement>' in text_response:
            start = text_response.find('<sql_statement>') + len('<sql_statement>')
            end = text_response.find('</sql_statement>')
            if end != -1:
                sql_query = text_response[start:end].strip()
        else:
            sql_query = text_response.strip()

        is_valid, validation_error = self.validate_sql(sql_query)
        if not is_valid:
            return None, f"SQL validation failed: {validation_error}"

        return sql_query, None

    def validate_sql(self, sql_query: str) -> tuple[bool, str]:
        try:
            parsed = sqlparse.parse(sql_query)
            if not parsed:
                return False, "Empty or invalid SQL query"
            
            statement = parsed[0]
            tokens = statement.tokens
            found_select = False
            for token in tokens:
                if (token.ttype is Keyword or str(token.ttype).startswith('Token.Keyword')) and token.value.upper() == 'SELECT':
                    found_select = True
                    break
            if not found_select:
                return False, "Only SELECT queries are allowed for security"
            
            forbidden_patterns = [
                r'\bCREATE\s+TABLE\b',
                r'\bCREATE\s+DATABASE\b',  
                r'\bCREATE\s+INDEX\b',
                r'\bDROP\b', r'\bDELETE\b', r'\bTRUNCATE\b', r'\bALTER\b',
                r'\bINSERT\b', r'\bUPDATE\b', r'\bGRANT\b', r'\bREVOKE\b'
            ]
            sql_upper = sql_query.upper()
            for pattern in forbidden_patterns:
                if re.search(pattern, sql_upper):
                    return False, f"Forbidden SQL operation detected: {pattern}"
            
            dangerous_patterns = [
                ';--', ';/*', 'UNION', 'INFORMATION_SCHEMA', 
                'pg_catalog', 'pg_stat', 'DROP', 'CREATE'
            ]
            for pattern in dangerous_patterns:
                if pattern in sql_upper:
                    return False, f"Potentially dangerous SQL pattern detected: {pattern}"

            try:
                formatted = sqlparse.format(sql_query, reindent=True)
                if not formatted.strip():
                    return False, "SQL query is empty after formatting"
            except Exception as e:
                return False, f"SQL syntax error: {str(e)}"
            
            return True, None
        except Exception as e:
            return False, f"SQL validation error: {str(e)}"