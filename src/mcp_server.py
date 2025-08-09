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
"""

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

mcp = FastMCP("sql-agent")
sql_agent = SQLAgent()

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
        return json.dumps({
            "success": True,
            "user_query": user_query,
            "generated_sql": sql_query,
            "validation_passed": True,
            "note": "SQL query generated and validated. Ready for database execution." # remove this later, once RDS instance is connected
        })
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