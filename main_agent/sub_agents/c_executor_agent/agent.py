from google.adk.agents import Agent

executor_agent = Agent(
    name="c_executor_agent",
    model="gemini-2.0-flash",
    instruction="Just a minimal test focus agent."
)
