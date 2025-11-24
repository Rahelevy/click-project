from google.adk.agents import Agent

intent_agent = Agent(
    name="a_intent_agent",
    model="gemini-2.0-flash",
    instruction="Just a minimal test intent agent."
)
