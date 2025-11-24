from google.adk.agents import Agent
from pydantic import BaseModel

class ExplanationInput(BaseModel):
    rows: list

class ExplanationOutput(BaseModel):
    explanation: str

explainer_agent = Agent(
    name="d_explanation_agent",
    model="gemini-2.0-flash",
    description="Stub Explanation Agent",
    instruction="""
        You are Agent D (Explanation Agent).

        STUB VERSION:
        When you receive SQL rows, return a simple explanation:
            "Here is your explanation of the results (stub)."
    """,

    input_schema=ExplanationInput,
    output_schema=ExplanationOutput,
    output_key="explanation",
)
