from main_agent.sub_agents.d_explanation_agent.agent import ExplainerAgent
from main_agent.sub_agents.d_explanation_agent.schemas import ExplanationInput, ExecutorResult

agent = ExplainerAgent()

test_input = ExplanationInput(
    user_question="תני לי קליקים לפי ימים",
    incoming=ExecutorResult(
        status="success",
        description="[]"
    )
)



out = agent.run(test_input)
print(out["state"].model_dump_json(indent=2, ensure_ascii=False))