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
    description="Focus Agent that asks for clarification when A sends needs_focus.",
    instruction="""
        You are Agent B (Focus Agent). Your job:

        - Receive the invalid question details from Agent A.
        - Ask the user ONE clarification question.
        - Produce a refined, clearer question.
    """,

    input_schema=FocusInput,
    output_schema=FocusOutput,
    output_key="refined_question",
)
