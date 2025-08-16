import logging
import json
import re
import boto3
from botocore.exceptions import ClientError
import sqlparse
from sqlparse.tokens import Keyword, DML, Punctuation

from prompt import create_system_prompt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Generates and validates SQL queries from a user's natural language query 
# using a Bedrock agent and a custom prompt
class SQLAgent:
    def __init__(self, model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0", region: str = "us-east-1"):
        self.model_id = model_id
        self.region = region
        self.bedrock_agent = boto3.client(service_name='bedrock-runtime', region_name=region)

    # Generates SQL query from user's natural language query    
    def generate_sql(self, user_query: str) -> tuple[str, str]:
        # Create system prompt for the Bedrock agent using the user's query  
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

        # Run the Bedrock agent using the prompt (Claude Sonnet 3.5)
        try:
            response = self.bedrock_agent.invoke_model(
                modelId=self.model_id,
                body=body
            )
        except (ClientError, Exception) as error:
            logger.error(f"ERROR: Can't invoke '{self.model_id}'. Reason: {error}")
            return None, f"Error invoking model: {error}"

        # Decode the response from the Bedrock agent
        decoded_response = json.loads(response["body"].read())
        text_response = decoded_response["content"][0]["text"]

        # Extract the SQL query from the response (contained in <sql_statement> tags)
        if '<sql_statement>' in text_response:
            start = text_response.find('<sql_statement>') + len('<sql_statement>')
            end = text_response.find('</sql_statement>')
            if end != -1:
                sql_query = text_response[start:end].strip()
        else:
            sql_query = text_response.strip()

        # Validate the SQL query
        is_valid, validation_error = self.validate_sql(sql_query)
        if not is_valid:
            return None, f"SQL validation failed: {validation_error}"

        return sql_query, None

    # Validates the SQL query to ensure it is safe and follows SQL syntax
    def validate_sql(self, sql_query: str) -> tuple[bool, str]:
        PROHIBITED_KEYWORDS = [
            "INSERT", "UPDATE", "DELETE", "MERGE", "UPSERT", "REPLACE",
            "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE",
            "CALL", "EXEC", "EXECUTE", "UNION", "INTERSECT", "EXCEPT", "MINUS",
            "BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "COPY", 
            "LOAD", "IMPORT", "EXPORT",
        ]
        PROHIBITED_SELECT_KEYWORDS = ["INTO"]
        DISALLOWED_SCHEMAS = [
            "INFORMATION_SCHEMA", "PG_CATALOG", "PG_TOAST", "PG_TEMP", "PG_TOAST_TEMP"
        ]
        DISALLOWED_TABLE_PREFIXES = ["PG_STAT"]

        if not isinstance(sql_query, str) or not sql_query.strip():
            return False, "Empty or invalid SQL string"

        statements = [s for s in sqlparse.parse(sql_query) if s.tokens and not s.is_whitespace]
        if not statements:
            return False, "Empty or invalid SQL query"
        if len(statements) != 1:
            return False, "Multiple statements are not allowed"
        stmt = statements[0]

        flat = []
        stack = list(stmt.tokens)
        while stack:
            t = stack.pop(0)
            if getattr(t, "is_group", False):
                stack = list(t.tokens) + stack
            else:
                flat.append(t)

        if (stmt.get_type() or "").upper() != "SELECT":
            return False, "Only SELECT queries are allowed"

        for t in flat:
            if (t.ttype in (Keyword, DML)) or str(t.ttype).startswith("Token.Keyword"):
                if t.value.upper() in PROHIBITED_KEYWORDS:
                    return False, "Query contains prohibited keywords (DDL/DML/set operations)"
        
        saw_select = False
        before_from = True
        for t in flat:
            if (t.ttype in (Keyword, DML)) or str(t.ttype).startswith("Token.Keyword"):
                val = t.value.upper()
                if val == "SELECT":
                    saw_select = True
                elif val == "FROM":
                    before_from = False
                elif saw_select and before_from and val in PROHIBITED_SELECT_KEYWORDS:
                    return False, "SELECT INTO is not allowed"

        mid_semicolon = any(t.ttype is Punctuation and t.value == ";" for t in flat)
        if mid_semicolon and not sql_query.strip().endswith(";"):
            return False, "Semicolons in the middle of the query are not allowed"
        
        sql_up = sql_query.upper()
        from_like_patterns = [
            r"\bFROM\s+(?:ONLY\s+)?(?P<obj>(?:\"[^\"]+\"|\w+)(?:\.(?:\"[^\"]+\"|\w+))?)",
            r"\bJOIN\s+(?:ONLY\s+)?(?P<obj>(?:\"[^\"]+\"|\w+)(?:\.(?:\"[^\"]+\"|\w+))?)",
        ]
        for pat in from_like_patterns:
            for m in re.finditer(pat, sql_up):
                obj = m.group("obj").strip()
                parts = [p[1:-1] if len(p) >= 2 and p[0] == '"' and p[-1] == '"' else p for p in obj.split(".")]
                parts = [p.strip() for p in parts if p.strip()]
                if not parts:
                    continue

                if len(parts) >= 2:
                    schema = parts[0]
                    if schema in DISALLOWED_SCHEMAS or schema.startswith("PG_"):
                        return False, f"Access to schema '{schema}' is not allowed"
                else:
                    tbl = parts[0]
                    if any(tbl.startswith(prefix) for prefix in DISALLOWED_TABLE_PREFIXES):
                        return False, f"Access to table '{tbl}' is not allowed"
        
        return True, None