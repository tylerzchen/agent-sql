import logging
import uvicorn
import json
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from mcp_server import (
    query_sql_agent, 
    execute_sql_query, 
    generate_sql_query
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# HTTP web adapter (wrapper) for the MCP server
# (allows for MCP client to connect to server over HTTP instead)
app = FastAPI(
    title="SQL Agent MCP Web Adapter",
    description="HTTP adapter for MCP SQL Agent server",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Model for MCP tool call request
class ToolCall(BaseModel):
    jsonrpc: str = "2.0"
    id: int
    method: str
    params: dict

# Model for MCP prompt call request
class PromptCall(BaseModel):
    jsonrpc: str = "2.0"
    id: int
    method: str
    params: dict

# Root endpoint for the MCP server
@app.get("/")
async def root():
    return {
        "service": "SQL Agent MCP Web Adapter",
        "status": "running",
        "description": "HTTP adapter for MCP SQL Agent server",
        "endpoints": [
            "GET /",
            "GET /health",
            "POST /tools/list",
            "POST /tools/call",
            "POST /prompts/list",
            "POST /prompts/call"
        ],
        "mcp_tools": [
            "query_sql_agent",
            "execute_sql_query"
        ],
        "mcp_prompts": [
            "generate_sql_query"
        ]
    }

# Health check endpoint for the MCP server
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "SQL Agent MCP Web Adapter",
        "transport": "HTTP",
        "timestamp": datetime.now().isoformat()
    }

# List all MCP tools available
@app.post("/tools/list")
async def list_tools():
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": [
            {
                "name": "query_sql_agent",
                "description": "Convert natural language query into a valid SQL query to be executed on the database.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_query": {
                            "type": "string",
                            "description": "Natural language query about the database"
                        }
                    },
                    "required": ["user_query"]
                }
            },
            {
                "name": "execute_sql_query",
                "description": "Execute a SQL query on the database and return the results.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sql_query": {
                            "type": "string",
                            "description": "SQL query to execute"
                        },
                        "user_query": {
                            "type": "string",
                            "description": "Original user query for context"
                        }
                    },
                    "required": ["sql_query", "user_query"]
                }
            }
        ]
    }

# Call a specific MCP tool by name and matching arguments
@app.post("/tools/call")
async def call_tool(request: ToolCall):
    try:
        tool_name = request.params.get("name")
        tool_args = request.params.get("arguments", {})
        logger.info(f"Calling tool: {tool_name} with args: {tool_args}")
        
        # Directly run the MCP tool functions here
        if tool_name == "query_sql_agent":
            result = await query_sql_agent(user_query=tool_args.get("user_query", ""))
        elif tool_name == "execute_sql_query":
            result = await execute_sql_query(
                sql_query=tool_args.get("sql_query", ""),
                user_query=tool_args.get("user_query", "")
            )
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }
        
        # Return the result of the MCP tool call
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "result": json.loads(result) if isinstance(result, str) else result
        }
    except Exception as error:
        logger.error(f"Error calling tool: {str(error)}")
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {
                "code": -32603,
                "message": f"Internal server error: {str(error)}"
            }
        }

# List all MCP prompts available
@app.post("/prompts/list")
async def list_prompts():
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": [
            {
                "name": "generate_sql_query",
                "description": "Convert natural language to SQL query",
                "arguments": {
                    "type": "object",
                    "properties": {
                        "user_query": {
                            "type": "string",
                            "description": "Natural language query about the database"
                        }
                    },
                    "required": ["user_query"]
                }
            }
        ]
    }

# Call a specific MCP prompt by name and arguments
@app.post("/prompts/call")
async def call_prompt(request: PromptCall):
    try:
        prompt_name = request.params.get("name")
        prompt_args = request.params.get("arguments", {})
        logger.info(f"Calling prompt: {prompt_name} with args: {prompt_args}")
        
        # Generate the SQL query system prompt using the user's query
        if prompt_name == "generate_sql_query":
            result = await generate_sql_query(user_query=prompt_args.get("user_query", ""))
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": result
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown prompt: {prompt_name}"
                }
            }
    except Exception as error:
        logger.error(f"Error calling prompt: {str(error)}")
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {
                "code": -32603,
                "message": f"Internal server error: {str(error)}"
            }
        }

# Run the MCP server adapter on local machine over HTTP (localhost)
if __name__ == "__main__":
    logger.info("Starting MCP server adapter...")
    uvicorn.run(app, host="0.0.0.0", port=8000)