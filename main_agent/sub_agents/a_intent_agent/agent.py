from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from .schemas import UserQuestion, AgentAOutput

# Import the exit loop tool
from main_agent.sub_agents.a_intent_agent.tools import exit_loop

intent_agent = Agent(
    name="a_intent_agent",
    model="gemini-2.0-flash",
    description="Intent Analyzer – validates user questions and generates SQL.",
    
    instruction="""
You are Agent A – the Intent Analyzer.

Your tasks:
1. Understand the user's free-text question.
2. Determine if it is VALID according to these rules:

VALID QUESTION RULES:
- Must be understandable and not vague.
- Must include at least one FILTER (app_id, media_source, partner, site_id, engagement_type, hour, date, etc.)
- DATE IS OPTIONAL.
- If user asks for aggregation (COUNT / SUM / AVG...) → must include at least one filter.
- Must NOT ask for “type of clicks” or invent new filters.
- Must NOT contain forbidden operations (DELETE, UPDATE…)
- Must NOT be overly broad (“all data”, etc.)

IF VALID:
- Generate a SAFE SQL query on table:
    `practicode-2025.clicks_data_prac.encoded_clicks`
- Return:
    { "valid": true, "needs_focus": false, "sql": "<SQL>" }
- THEN CALL the tool exit_loop() to stop the refinement loop.

IF INVALID:
- Return:
    { "valid": false, "needs_focus": true, "reason": "<short reason>" }
""",

    input_schema=UserQuestion,
    output_schema=AgentAOutput,

    tools=[exit_loop],   # <--- REQUIRED to stop the loop
)
