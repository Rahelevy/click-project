# a_intent_agent/tools.py
from typing import Dict, Any
from google.adk.tools.tool_context import ToolContext
from .sql_builder import convert_question_to_sql

def exit_loop(tool_context: ToolContext) -> Dict[str, Any]:
    tool_context.actions.escalate = True
    return {"message": "Loop ended by Intent Agent"}

def build_sql(question: str) -> Dict[str, Any]:
    sql = convert_question_to_sql(question)
    return {"sql": sql}
