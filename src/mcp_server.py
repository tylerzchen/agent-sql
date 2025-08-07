import logging
from mcp.server.fastmcp import FastMCP

logging.info("Starting MCP Server")

mcp = FastMCP("sql-agent")

if __name__ == "__main__":
    mcp.run(transport="stdio")