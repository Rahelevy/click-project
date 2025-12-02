from main_agent.sub_agents.a_intent_agent.agent import IntentAgent
from main_agent.sub_agents.a_intent_agent.schemas import AgentAOutput

agent_a = IntentAgent()

# 2. Prepare a test state (just like ADK would)
state = AgentAOutput(
    question="show me all the clicks for app id 20 on october 2025"
)

# 3. Run it directly
result = agent_a.run(state)

print(result)
print(result["state"])
