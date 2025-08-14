import os
import logging
import json
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from prompt import create_system_prompt, create_error_prompt
from sql_agent import SQLAgent
from rds_client import RDSClient
from errors import generate_error_response

load_dotenv()

# Get environment variables for RDS instance (replace in .env)
CLUSTER_ARN = os.getenv("AURORA_CLUSTER_ARN")
SECRET_ARN = os.getenv("AURORA_SECRET_ARN")
DB_NAME = os.getenv("DATABASE_NAME")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

mcp = FastMCP("sql-agent")
sql_agent = SQLAgent()

# Test the connection to the RDS instance before starting the MCP server
connection_success, connection_error = None, None
try:
    rds_client = RDSClient(cluster_arn=CLUSTER_ARN, secret_arn=SECRET_ARN, db_name=DB_NAME)
    connection_success, connection_error = rds_client.test_connection()
    if not connection_success:
        logger.error(f"Failed to connect to RDS: {connection_error}")
    else:
        logger.info("Connection to RDS successful")
except Exception as error:
    connection_success = False
    connection_error = f"Failed to connect to RDS: {str(error)}"
    logger.error(f"Failed to connect to RDS: {connection_error}")

# MCP prompt used to generate valid SQL queries given the user's query 
# (uses the system prompt)
@mcp.prompt("Generate SQL Query")
async def generate_sql_query(user_query: str) -> str:
    """Convert a natural language query into a valid SQL query to be executed on the database.

    This prompt is used to help Claude generate SQL queries baesd on the user's query and
    the database schema. Use this when you need to convert a natural language query into SQL.

    Args:
        user_query: the natural language query about the database (e.g., "Show me all tickets that are overdue and still unresolved")
    """
    return create_system_prompt(user_query=user_query)

# MCP prompt used to correct the SQL query after an error occurs
# (uses the system prompt and error prompt)
@mcp.prompt("Fix SQL Query Error")
async def fix_sql_query_error(user_query: str, error_context: dict, generated_sql: str = "") -> str:
    """Fix a SQL query that failed to execute or validate due to an error.

    This prompt is used to help Claude correct a SQL query that failed to execute or validate due to an error using
    specific error context to help fix the query rather than rewriting the entire query from scratch.
    Use this when you need to fix a SQL query that failed to execute or validate due to an error.

    Args:
        user_query: the original natural language query that generated the SQL query for context
        error_context: a dictionary containing detailed error information including error type, message, and recovery steps
        generated_sql: the SQL query that failed to execute or validate (if available)
    """
    return create_error_prompt(
        user_query=user_query,
        error_context=error_context,
        generated_sql=generated_sql
    )

# MCP tool used to convert a user's natural language query into a SQL query 
# (uses the generate_sql_query prompt)
@mcp.tool()
async def query_sql_agent(
    user_query: str,
    previous_error: str = None,
    error_context: str = None
) -> str:
    """Convert a natural language query into a valid SQL query to be executed on the database.

    This tool is used to convert a natural language query related to the following
    database tables -- tickets, ticket categories, ticket priorities, ticket statuses, 
    messages, message types -- into a secure and validated PostgreSQL SELECT query,
    then execute the query on the database and return the results.

    IMPORTANT WORKFLOW:
    - FIRST ATTEMPT: Call this tool with the user_query parameter only to get the initial system prompt.
    - IF ERROR OCCURS: Use the retry_instructions from the error response to call this tool again.
    - RETRY ATTEMPT: Call this tool with the previous_error and error_context parameters to generate an error-aware prompt.
    - FINAL STEP: Call execute_sql_query with the generated SQL query to execute it on the database and return the results.

    RETRY INSTRUCTIONS:
    When you receive an error response, look for the "retry_instructions" field in the response and follow the instructions.
    This will call this query_sql_agent tool again with the error context and previous error message to generate a better prompt for fixing the issue.
    
    Args:
        user_query: the natural language query about the database (e.g., "Show me all tickets that are overdue and still unresolved")
        previous_error: (optional) the error message from the previous attempt to generate a SQL query - use this for retries
        error_context: (optional) a dictionary containing detailed error context from the previous attempt to generate a SQL query - use this for retries
    """
    # Verify the connection to the RDS instance
    if not connection_success:
        logger.error(f"Database connection not available: {connection_error}")
        return json.dumps({
            "success": False,
            "error": f"Database service unavailable: {connection_error}",
            "user_query": user_query,
            "retry_advice": "The database service is currently unavailable. Please try again later.",
            "error_type": "connection_error"
        }, indent=2)

    # Check if this is a retry attempt and handle it accordingly
    if previous_error and error_context:
        try:
            # Parse the error context from the previous error response
            parsed_error_context = json.loads(error_context)
            generated_sql = parsed_error_context.get("context", {}).get("generated_sql", "")

            # Generate an error-aware prompt using the fix_sql_query_error prompt
            system_prompt = create_error_prompt(
                user_query=user_query,
                error_context=parsed_error_context,
                generated_sql=generated_sql
            )
            return json.dumps({
                "success": True,
                "message": "Error-aware prompt generated successfully. Use this prompt to generate a new SQL query that fixes the previous SQL generation issue.",
                "system_prompt": system_prompt,
                "next_step": "Call execute_sql_query with the newly generated SQL", 
                "user_query": user_query,
                "previous_error": previous_error,
                "is_retry": True,
                "instructions": [
                    "1. Use the error context above to understand what went wrong",
                    "2. Use the new system prompt to generate corrected SQL that addresses the specific error",
                    "3. Extract the SQL from the <sql_statement> tags",
                    "4. Call execute_sql_query with the corrected SQL and user_query"
                ]
            }, indent=2)
        except Exception as error:
            logger.error(f"Error generating an error-aware prompt: {str(error)}")
            pass
    
    # Generate the system prompt and return it to the MCP client
    try:
        system_prompt = create_system_prompt(user_query=user_query)
        return json.dumps({
            "success": True,
            "message": "Please use the following prompt to generate SQL, then call execute_sql_query with the result:",
            "system_prompt": system_prompt,
            "next_step": "Call execute_sql_query with the generated SQL",
            "user_query": user_query,
            "instructions": [
                "1. Use the system_prompt above to generate valid SQL",
                "2. Extract the SQL from the <sql_statement> tags",
                "3. Call execute_sql_query with the generated SQL and user_query"
            ]
        }, indent=2)
    except Exception as error:
        logger.error(f"Error generating system prompt: {str(error)}")
        return generate_error_response(
            error_type="sql_generation_error",
            error_message=f"Failed to generate system prompt: {str(error)}",
            user_query=user_query
        )

# MCP tool used to execute a SQL query on the RDS instance and return 
# the results (uses the generate_sql_query prompt)
@mcp.tool()
async def execute_sql_query(sql_query: str, user_query: str = "") -> str:
    """Execute a SQL query on the database and return the results.

    This tool is used to execute pre-generated SQL queries on the database.
    The SQL query should be generated by Claude using the generate_sql_query prompt,
    based on the database schema and the user's query.

    Args:
        sql_query: the SQL query to execute on the database
        user_query: the original natural language query that generated the SQL query for context (optional)
    """
    # Verify the connection to the RDS instance
    if not connection_success:
        logger.error(f"Database connection not available: {connection_error}")
        return json.dumps({
            "success": False,
            "error": f"Database service unavailable: {connection_error}",
            "sql_query": sql_query,
            "user_query": user_query,
            "retry_advice": "The database service is currently unavailable. Please try again later.",
            "error_type": "connection_error"
        }, indent=2)

    try:
        # Validate the generated SQL query from the query_sql_agent tool
        is_valid, error = sql_agent.validate_sql(sql_query)
        if not is_valid:
            logger.error(f"Invalid SQL query: {error}")
            return generate_error_response(
                error_type="sql_validation_error",
                error_message=f"Invalid SQL query: {error}",
                user_query=user_query,
                context={
                    "generated_sql": sql_query,
                    "validation_error": error,
                    "sql_length": len(sql_query)
                }
            )
        
        # Execute the SQL query on the RDS instance and return the results
        result = rds_client.execute_query(sql_query)
        if not result['success']:
            logger.error(f"Database query failed: {result['error']}")
            return generate_error_response(
                error_type="database_error",
                error_message=f"Database query failed: {result['error']}",
                user_query=user_query,
                context={
                    "generated_sql": sql_query,
                    "database_error": result['error'],
                    "error_code": result.get('error_code', 'unknown'),
                    "query_type": "SELECT"
                }
            )
        
        # Return the results of the SQL query to the MCP client
        return json.dumps({
            "success": True,
            "user_query": user_query,
            "generated_sql": sql_query,
            "validation_passed": True,
            "data": result['data'],
            "row_count": result['row_count'],
            "columns": result['columns'],
        }, indent=2, default=str)
    except Exception as error:
        logger.error(f"Unexpected error in execute_sql_query: {str(error)}")
        return generate_error_response(
            error_type="sql_generation_error",
            error_message=f"Unexpected error: {str(error)}",
            user_query=user_query,
            context={
                "generated_sql": sql_query,
                "error_details": str(error),
                "operation": "sql_query_execution"
            }
        )

# Run the MCP server on local machine using stdio transport
if __name__ == "__main__":
    logger.info("Starting MCP server...")
    mcp.run(transport="stdio")