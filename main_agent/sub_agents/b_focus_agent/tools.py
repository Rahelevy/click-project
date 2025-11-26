# b_focus_agent/tools.py
from typing import Dict, Any
from google.adk.tools.tool_context import ToolContext

def exit_loop(tool_context: ToolContext) -> Dict[str, Any]:
    tool_context.actions.escalate = True
    return {"message": "Stopping loop to wait for user clarification"}
