import os
import logging
import json
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from sql_agent import SQLAgent
from rds_client import RDSClient

load_dotenv()

CLUSTER_ARN = os.getenv("AURORA_CLUSTER_ARN")
SECRET_ARN = os.getenv("AURORA_SECRET_ARN")
DB_NAME = os.getenv("DATABASE_NAME")

"""
test_queries = [
    “Show all ACME tickets that are High priority and currently in an open status”
    “For each organization, give me the count of tickets by status name”
    “List tickets resolved in the last 7 days.”
    “Which tickets are due in the next 3 days and not closed?”
    “Show all tickets marked as special cases”
    “For Globex, list each ticket with the count of public vs. internal messages”
    “Find tickets whose tags include either API or SMS”
    “Show ticket counts per agent across all organizations, including agents with zero tickets. Sort by count descending, then agent name.”
    “Return all tickets where custom_fields.org = 'initech' and the seq value is between 1 and 5”
    “Give me the last 10 public messages across all orgs, with ticket number, message type, and whether the author is an agent or a user.”
]
"""

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

mcp = FastMCP("sql-agent")
sql_agent = SQLAgent()
rds_client = RDSClient(
    cluster_arn=CLUSTER_ARN,
    secret_arn=SECRET_ARN,
    db_name=DB_NAME
)

@mcp.tool()
async def query_sql_agent(user_query: str) -> str:
    """Convert a natural language query into a valid SQL query to be executed on the database.

    This tool is used to convert a natural language query related to the following
    database tables -- tickets, ticket categories, ticket priorities, ticket statuses, 
    messages, message types -- into a secure and validated PostgreSQL SELECT query.
    
    Args:
        user_query: the natural language query about the database (e.g., "Show me all tickets that are overdue and still unresolved")
    """
    try:
        sql_query, error = sql_agent.generate_sql(user_query)
        if error:
            logger.error(f"Error generating SQL query: {error}")
            return json.dumps({
                "success": False,
                "error": error,
                "user_query": user_query
            }, indent=2)
        
        logger.info(f"Generated SQL query: {sql_query}")
        
        connection_success, error = rds_client.test_connection()
        if not connection_success:
            logger.error(f"Error connecting to RDS: {error}")
            return json.dumps({
                "success": False,
                "error": f"Error connecting to the database: {error}",
                "user_query": user_query,
                "generated_sql": sql_query,
                "data": None,
                "row_count": 0,
                "columns": []
            })
        
        result = rds_client.execute_query(sql_query)
        if not result['success']:
            logger.error(f"Database query failed: {result['error']}")
            return json.dumps({
                "success": False,
                "error": f"Database query failed: {result['error']}",
                "user_query": user_query,
                "generated_sql": sql_query,
                "data": None,
                "row_count": 0,
                "columns": []
            })
        
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
        logger.error(f"Unknown error: {str(error)}")
        return json.dumps({
            "success": False,
            "error": str(error),
            "user_query": user_query,
            "generated_sql": None
        }, indent=2)

if __name__ == "__main__":
    logger.info("Starting MCP server...")
    mcp.run(transport="stdio")