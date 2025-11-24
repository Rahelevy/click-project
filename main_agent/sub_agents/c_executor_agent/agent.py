from google.adk.agents import Agent
from pydantic import BaseModel

class SQLRequest(BaseModel):
    sql: str

class SQLResult(BaseModel):
    rows: list

executor_agent = Agent(
    name="c_executor_agent",
    model="gemini-2.0-flash",
    description="Stub SQL Executor Agent.",
    instruction="""
        You are Agent C (SQL Executor).

        STUB VERSION:
        When you receive a SQL query, DO NOT execute it.
        Respond with:
            rows = []
    """,

    input_schema=SQLRequest,
    output_schema=SQLResult,
    output_key="rows",
)
