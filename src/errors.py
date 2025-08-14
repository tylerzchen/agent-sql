import json
from typing import Dict, List

def generate_error_response(
    error_type: str, 
    error_message: str, 
    user_query: str,
    context: Dict = None
) -> str:
    error_templates = {
        "sql_generation_error": {
            "title": "SQL Generation Failed",
            "common_causes": [
                "Unclear table relationships in the query",
                "Missing or ambiguous column references",
                "Complex query logic that needs to be simplified",
                "Unsupported SQL syntax or operations"
            ],
            "recovery_steps": [
                "Break down the query into smaller steps",
                "Specify the exact table and column names",
                "Use more specific language about what you want to retrieve",
                "Consider asking for data from one table at a time"
            ]
        },
        "sql_validation_error": {
            "title": "SQL Validation Failed",
            "common_causes": [
                "Non-SELECT operations were detected in the query",
                "Security violations (DROP, CREATE, etc.)",
                "SQL syntax errors",
                "Dangerous patterns detected (DELETE, TRUNCATE, UPDATE, etc.)"
            ],
            "recovery_steps": [
                "Ensure you are only requesting data (SELECT operations)",
                "Check for proper SQL syntax",
                "Avoid using multiple statements or complex operations",
                "Focus on retrieving existing data only"
            ]
        },
        "database_error": {
            "title": "Database Query Execution Failed",
            "common_causes": [
                "Table or column name doesn't exist",
                "Invalid JOIN conditions",
                "Data types are mismatched",
                "Missing or invalid WHERE conditions",
                "Permission issues or missing privileges"
            ],
            "recovery_steps": [
                "Verify the table and column names exist in the schema",
                "Check the JOIN conditions between tables", 
                "Ensure data types match in comparisons",
                "Simplify the query to focus on one table at a time"
            ]
        }
    }

    error_template = error_templates.get(error_type, error_templates["sql_generation_error"])
    retry_instructions = f"""
    TO RETRY WITH ERROR CONTEXT:
    Call the query_sql_agent tool with the following parameters:
    - user_query: "{user_query}"
    - previous_error: "{error_message}"
    - error_context: {json.dumps(context, indent=2)}
    """
    response = {
        "success": False,
        "error_type": error_type,
        "error_title": error_template["title"],
        "error_message": error_message,
        "user_query": user_query,
        "context": context or {},
        "recovery_steps": error_template["recovery_steps"],
        "common_causes": error_template["common_causes"],
        "retry_advice": f"Try rephrasing your query to be more specific about: {', '.join(error_template['recovery_steps'])}",
        "retry_instructions": retry_instructions
    }

    return json.dumps(response, indent=2)