import re
from typing import Any, Dict, List, Optional
from google.cloud import bigquery
from google.adk.tools.tool_context import ToolContext

FORBIDDEN = re.compile(r"\b(DELETE|UPDATE|INSERT|MERGE|DROP|ALTER|TRUNCATE|CREATE)\b", re.I)

def run_bigquery(sql: str) -> List[Dict[str, Any]]:
    if FORBIDDEN.search(sql):
        raise ValueError("Forbidden SQL operation detected.")

    client = bigquery.Client()
    job = client.query(sql)
    rows = job.result()
    return [dict(row.items()) for row in rows]

def execute_sql(input_data: Optional[Dict[str, Any]] = None, tool_context: ToolContext = None) -> Dict[str, Any]:
    """
    Executes SQL stored in tool_context.state and returns raw results
    in the exact format Agent D expects.
    """
    input_data = input_data or {}

    sql = input_data.get("sql") or tool_context.state.get("sql")
    user_question = input_data.get("user_question") or tool_context.state.get("user_question")

    try:
        if not sql or not user_question:
            raise ValueError("Missing sql or user_question in state.")

        result = run_bigquery(sql)

        return {
            "user_question": user_question,
            "db_result": result,
            "row_count": len(result),
        }

    except Exception as e:
        # חשוב: מחזירים עדיין את אותו מבנה כדי לעצור לופים
        return {
            "user_question": user_question or "",
            "db_result": [],
            "row_count": 0,
        }