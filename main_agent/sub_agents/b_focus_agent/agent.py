from google.adk.agents import Agent
from pydantic import BaseModel

class FocusInput(BaseModel):
    valid: bool
    needs_focus: bool
    reason: str | None = None

class FocusOutput(BaseModel):
    refined_question: str

focus_agent = Agent(
    name="b_focus_agent",
    model="gemini-2.0-flash",
    description="Focus Agent that asks clarification when A needs focus.",

    instruction="""
        You are Agent B (Focus Agent).

        RETURN STRICT JSON:
        {
          "refined_question": "<new clearer question>"
        }

        ONLY ask for ONE clarification.
        NEVER talk about "types of clicks" or invent categories.

        If Agent A says the question is vague:
          - Reformulate the question into a more precise version.
          - Add the missing detail mentioned in reason.
    """,

    input_schema=FocusInput,
    output_schema=FocusOutput,
    output_key="refined_question",
)
