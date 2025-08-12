import requests
import json

BASE_URL = "http://localhost:8000"

def test_tools_list():
    response = requests.post(f"{BASE_URL}/tools/list", json={})
    print("=== Tools List ===")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_tools_call():
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "query_sql_agent",
            "arguments": {
                "user_query": "Show me all tickets concerning the ACME organization"
            }
        }
    }
    response = requests.post(f"{BASE_URL}/tools/call", json=payload)
    print("=== Tools Call ===")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_prompts_list():
    response = requests.post(f"{BASE_URL}/prompts/list", json={})
    print("=== Prompts List ===")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_prompts_call():
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "prompts/call",
        "params": {
            "name": "generate_sql_query",
            "arguments": {
                "user_query": "Show me all tickets concerning the ACME organization"
            }
        }
    }
    response = requests.post(f"{BASE_URL}/prompts/call", json=payload)
    print("=== Prompts Call ===")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

if __name__ == "__main__":
    print("Testing SQL Agent MCP Web Adapter...\n")
    test_tools_list()
    test_tools_call()
    test_prompts_list()
    test_prompts_call()
    print("\nAll tests completed successfully.")