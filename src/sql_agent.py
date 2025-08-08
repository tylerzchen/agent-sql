import logging
import json
import boto3
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
def generate_sql(bedrock_agent, user_query: str) -> tuple[str, str]:
    model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
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
        response = bedrock_agent.invoke_model(
            modelId=model_id,
            body=body
        )
    except (ClientError, Exception) as error:
        logger.error(f"ERROR: Can't invoke '{model_id}'. Reason: {error}")
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

    is_valid, validation_error = validate_sql(sql_query)
    if not is_valid:
        return None, f"SQL validation failed: {validation_error}"

    return sql_query, None

# TODO: Add error handling, if invalid SQL, run the model again with an error prompt
def validate_sql(sql_query: str) -> tuple[bool, str]:
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
        
        forbidden_keywords = [
            'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 
            'UPDATE', 'GRANT', 'REVOKE', 'EXECUTE', 'EXEC', 'MERGE'
        ]
        sql_upper = sql_query.upper()
        for keyword in forbidden_keywords:
            if keyword in sql_upper:
                return False, f"Forbidden SQL operation detected: {keyword}"
        
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

def main():
    bedrock_agent = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')

    test_queries = [
        "Show all tickets marked as cases that are overdue and still unresolved.",
        "List all agents who have responded to at least one ticket in the last 30 days.",
        "How many tickets have been created via the AI channel in the last week?",
        "Get the average time to first response for resolved tickets.",
        "Find the 5 most recent internal notes added to tickets.",
        "List all tickets tagged with 'urgent' and their current status.",
        "Show all message types and how many messages fall under each type.",
        "Find all categories with more than 10 active tickets.",
        "Get the subject and body of the first message in each ticket.",
        "How many tickets are assigned to agents versus unassigned?"
    ]
    sql_result, error = generate_sql(bedrock_agent, test_queries[0])
    if error:
        logger.error(f"Error: {error}")
    else:
        logger.info(sql_result)

if __name__ == "__main__":
    main()