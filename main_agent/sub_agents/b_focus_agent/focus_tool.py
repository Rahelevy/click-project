from google.adk.tools.tool_context import ToolContext
from .schemas import AgentBInput, AgentBOutput, FocusToolInput
from .focus_logic import focus_logic


def focus_tool(data: FocusToolInput, tool_context: ToolContext) -> AgentBOutput:
    return focus_logic(
        input_data=data.input_data,
        user_answer=data.user_answer
    )
