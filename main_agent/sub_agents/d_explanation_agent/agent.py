from google.adk.agents import Agent

explainer_agent = Agent(
    name="d_explanation_agent",
    model="gemini-2.0-flash",
    instruction="Just a minimal test explanation agent."
)
