
# SQL Agent MCP Server

## Description

An MCP server used to convert natural language queries to secure/validated SQL
queries that are executed on an Aurora RDS (v2) PostgreSQL instance via the Data API. Supports both local development (stdio transport) and production deployment (HTTP transport via Lambda function + API gateway). Testable via any MCP client (e.g., Claude Desktop)

## Architecture

Claude Desktop (User Query) -> API Gateway -> Lambda Function -> HTTP Adapter -> MCP Server -> Data API -> Aurora RDS Instance -> PostgreSQL Tables

## File Structure

- **agent_sql/agent_sql_stack.py**: AWS CDK infrastructure definition (VPC + Aurora connection, RDS Proxy, Lambda, API Gateway)
- **src/mcp_server.py**: MCP server implementation with tools and prompts
- **src/sql_agent.py**: SQL generation and validation logic class (includes Bedrock implementation, not being used for now)
- **src/prompt.py**: Custom system prompt for SQL generation using database schema and the user's query
- **src/rds_client.py**: DB client for Aurora RDS PostgreSQL instance using the Data API
- **src/schema.sql**: Complete database schema with tables, relationships, and field descriptions
- **src/adapter.py**: FastAPI HTTP adapter for Lambda deployment
- **src/lambda_handler.py**: Lambda entry point/handler for HTTP adapter (using Magnum)

## Environment Variables

- AURORA_CLUSTER_ARN: ARN of Aurora Serverless v2 cluster (find in console)
- AURORA_SECRET_ARN: ARN of the Secrets Manager secret containing DB credentials (find in console)
- DATABASE_NAME: name of the PostgreSQL database (default: "postgres")
* Copy contents of env-template.txt file into .env and fill in values

## MCP Server Tools & Prompts

### Available Tools: 
- **`query_sql_agent`**: Converts natural language query from user to SQL and provides execution instructions to MCP client
- **`execute_sql_query`**: Validates and executes SQL queries on the RDS instance and returns formatted results

### Available Prompts:
- **`generate_sql_query`**: system prompt that helps MCP client's LLM generate valid SQL based on the database schema and provided examples

## API Reference (FastAPI HTTP Adapter)

### Endpoints:
- `GET /` - service information
- `GET /health` - health check
- `POST /tools/list` - list available MCP tools
- `POST /tools/call` - execute MCP tools by name and args
- `POST /prompts/list` - list available MCP prompts
- `POST /prompts/call` - execute MCP prompts by name and args

### Request Format (for calling tools/prompts):
* All tool and prompt calls use JSON-RPC 2.0 format:
```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "call",
    "params": {
        "name": "tool_name",
        "arguments": {}
    }
}
```

### Response format (formatted results)
```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "success": true,
        "data": [],
        "row_count": 5,
        "columns": []
    }
}
```

## Installation & Setup

### 1. Prerequisites
- **Python 3.10+**
- **AWS CLI** - configured with appropriate IAM perms and credentials
- **AWS CDK** - `npm install -g aws-cdk`
- **Docker**
- **Git** (optional)

### 2. Setup and activate the environment
```bash
python3 -m venv .venv
source .venv/bin/activate # On Windows: .venv/Scripts/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Configure AWS credentials (CDK)
* Note: this assumes you already the following setup in your CDK stack: Aurora Serverless v2 cluster (Data API enabled), VPC, RDS proxy, and security groups
* Note: get necessary access key values from your console, and make sure the target regions match (won't work otherwise)
```bash
aws --version
aws configure # load credentials
aws configure --profile my-profile # Alt: configure specific profile
aws sts get-caller-identity # verify credentials are working
# Verify AWS permissions
aws ec2 describe-regions
aws rds describe-db-clusters
aws lambda list-functions
aws cloudformation list-stacks
```

### 4. Edit database schema and system prompt if needed
- DB schema: **src/schema.sql**
- System prompt: **src/prompt.py**
- Ensure Aurora cluster is running, and RDS instance is active
- Confirm RDS Data API is enabled on the cluster

### 5. Test MCP server locally (Claude Desktop)
- Start the server ->
```bash
cd src
python3 mcp_server.py
```
- Verify its running, and then replace the contents of the Developer config file (Claude Desktop -> Settings -> Developer -> Local MCP Server -> Edit Config) with the contents of the **config/mcp_client_config_stdio.json** file (replace file paths to your own paths in the "command" and "args" props)
- The tools should show up and activate when you run a prompt in Claude now

### 6. Test HTTP adapter locally (curl)
- Start the server -> 
```bash
cd src
python3 adapter.py
```
- Test the endpoints in bash (replace port number if necessary):
```bash
# GET /health
curl http://localhost:8000/health
# GET /
curl http://localhost:8000/
# POST /tools/list
curl -X POST http://localhost:8000/tools/list
# POST /prompts/list
curl -X POST http://localhost:8000/prompts/list
# POST /tools/call (query_sql_agent tool)
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "call",
    "params": {
      "name": "query_sql_agent",
      "arguments": {
        "user_query": "Show me all tickets"
      }
    }
  }'
# POST /tools/call (execute_sql_query tool)
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "call",
    "params": {
      "name": "execute_sql_query",
      "arguments": {
        "sql_query": "SELECT * FROM tickets LIMIT 5",
        "user_query": "Show me 5 tickets"
      }
    }
  }'
# POST /prompts/call (generate_sql_query prompt)
curl -X POST http://localhost:8000/prompts/call \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "call",
    "params": {
      "name": "generate_sql_query",
      "arguments": {
        "user_query": "Show me tickets that are overdue"
      }
    }
  }'
```

## Deployment (Lambda)

### 1. Verify CDK stack setup, environment variables, and Docker setup
```bash
# Check that environment variables are loaded
python3 -c "import os; print('AURORA_CLUSTER_ARN:', os.getenv('AURORA_CLUSTER_ARN'))"
python3 -c "import os; print('AURORA_SECRET_ARN:', os.getenv('AURORA_SECRET_ARN'))"
python3 -c "import os; print('DATABASE_NAME:', os.getenv('DATABASE_NAME'))"

# Verify Docker is running
docker --version
docker ps

# Check SDK installation
cdk --version

# Verify AWS credentials
aws sts get-caller-identity

# Build and test Docker image locally
docker build -t mcp-lambda .
docker buildx build --platform linux/amd64 -t mcp-lambda . --load # use this if running into issues on Mac
docker run --rm mcp-lambda python3 -c "from lambda_handler import lambda_handler; print('✅ Lambda handler import successful')"
docker run --rm mcp-lambda python3 -c "from adapter import app; print('✅ FastAPI app import successful')"
docker run --rm mcp-lambda ls -la
docker run --rm mcp-lambda python3 -c "import os; print('Working directory:', os.getcwd()); print('Files:', os.listdir('.'))"
```

### 2. Bootstrap CDK
```bash
# Bootstrap CDK in your AWS account/region (first time only)
cdk bootstrap
```

### 3. Deploy infrastructure
```bash
# Deploy the complete stack
cdk deploy
```

### 4. Get the API gateway endpoint
- After successful deployment, CDK will output the endpoints -> 
- AgentSqlStack.MCPApiGatewayEndpoint = https://abc123.execute-api.us-east-1.amazonaws.com/prod/
- AgentSqlStack.AuroraClusterEndpoint = your-aurora-cluster.cluster-xyz.us-east-1.rds.amazonaws.com
- AgentSqlStack.RDSProxyEndpoint = your-proxy.proxy-xyz.us-east-1.rds.amazonaws.com

### 5. Test the API gateway endpoint (curl)
```bash
# GET /health
curl http://{your_API_gateway_URL}/health
# GET /
curl http://{your_API_gateway_URL}/
# POST /tools/list
curl -X POST http://{your_API_gateway_URL}/tools/list
# POST /prompts/list
curl -X POST http://{your_API_gateway_URL}/prompts/list
# POST /tools/call (query_sql_agent tool)
curl -X POST http://{your_API_gateway_URL}/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "call",
    "params": {
      "name": "query_sql_agent",
      "arguments": {
        "user_query": "Show me all tickets"
      }
    }
  }'
# POST /tools/call (execute_sql_query tool)
curl -X POST http://{your_API_gateway_URL}/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "call",
    "params": {
      "name": "execute_sql_query",
      "arguments": {
        "sql_query": "SELECT * FROM tickets LIMIT 5",
        "user_query": "Show me 5 tickets"
      }
    }
  }'
# POST /prompts/call (generate_sql_query prompt)
curl -X POST http://{your_API_gateway_URL}/prompts/call \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "call",
    "params": {
      "name": "generate_sql_query",
      "arguments": {
        "user_query": "Show me tickets that are overdue"
      }
    }
  }'
```

## Useful References

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/docs/getting-started/intro) - MCP Docs
- [AWS Boto3 Client](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) - AWS Boto3 Python SDK for accessing RDS, Bedrock, etc.
- [AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html) - General AWS Lambda docs
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Python SDK for MCP
- [FastAPI](https://fastapi.tiangolo.com/) - FastAPI docs
- [AWS CDK](https://docs.aws.amazon.com/cdk/api/v2/python/) - Python SDK for AWS CDK
- [Anthropic Prompt Engineering Guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) - Guide for prompt engineering with Claude models
- [HTTP Web Adapter for MCP Server](https://github.com/awslabs/aws-lambda-web-adapter/tree/main/examples/fastapi) - Sample repo for building a HTTP web adapter for MCP server