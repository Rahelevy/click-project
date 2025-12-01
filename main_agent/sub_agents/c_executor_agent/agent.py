from google.adk.agents import Agent
from .schemas import AgentCInput , AgentCOutput  # אין output_schema פה
from .tools import execute_sql

executor_agent = Agent(
    name="c_executor_agent",
    model="gemini-2.5-flash",
    description="SQL Executor – runs safe SQL on BigQuery and returns raw results.",
    instruction="""
You are Agent C – SQL Executor.

You MUST call execute_sql() exactly once.

Inputs arrive via tool_context.state:
sql
user_question

Steps:
1) Call execute_sql(input_data={})  (the tool reads from state).
2) Return ONLY the tool JSON as-is.

Never call any tool twice.
Never write your own text.
""",
    input_schema=AgentCInput,
    output_schema=AgentCOutput,
    tools=[execute_sql],
)