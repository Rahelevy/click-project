import os
from main_agent.sub_agents.d_explanation_agent.agent import ExplainerAgent
from main_agent.sub_agents.d_explanation_agent.schemas import ExplanationInput, ExecutorResult

print("API?", bool(os.getenv("GOOGLE_API_KEY")))

agent = ExplainerAgent()

test_input = ExplanationInput(
    user_question="תראי לי קליקים לפי ימים",
    incoming=ExecutorResult(
        status="success",
        description='[{"date":"2025-03-01","clicks":10},{"date":"2025-03-02","clicks":12}]'
    )
)

out = agent.run(test_input)
print(out["state"].model_dump_json(indent=2, ensure_ascii=False))
