from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

# Import sub-agents
from .sub_agents.a_intent_agent.agent import intent_agent
from .sub_agents.b_focus_agent.agent import focus_agent
from .sub_agents.c_executor_agent.agent import executor_agent
from .sub_agents.d_explanation_agent.agent import explainer_agent


root_agent = Agent(
    name="root_manager",
    model="gemini-2.0-flash",
    description="Root manager agent responsible for routing user queries.",
    
    instruction="""
    You are the ROOT MANAGER agent.

    ROUTING RULES:

    1. If the user question matches a predefined FAQ:
        → Immediately send the corresponding SQL query directly to Agent 3 (SQL Executor).
        → Do NOT validate or refine FAQ questions.

    2. If the question is a free-text user question:
        → Always delegate it to Agent A (Intent Analyzer) for validation and SQL creation.

    3. You must NEVER produce SQL or explanations yourself.
       Your only job is routing the conversation to the correct agent.

    """,

    # The only agent that should receive initial free-text questions
    sub_agents=[
        intent_agent,     # Agent A
        focus_agent,      # Used via A, not directly from the user
        executor_agent,   # Agent C
        explainer_agent,
    ],

    # tools=[
    #     AgentTool(faq_sql_tool),   # FAQs → predefined SQL
    #     AgentTool(run_sql_tool),   # BigQuery SQL executor
    # ],
)
