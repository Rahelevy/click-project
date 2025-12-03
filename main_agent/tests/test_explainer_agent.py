from main_agent.sub_agents.d_explanation_agent.agent import ExplainerAgent
from main_agent.sub_agents.d_explanation_agent.schemas import (
    ExplanationInput,
    ExecutorResult
)


# ---------------------------------------
# DIRECT RUN — like your IntentAgent test
# ---------------------------------------

# 1. Create agent
agent = ExplainerAgent()

# 2. Create a test state (success)
state_success = ExplanationInput(
    user_question="how many clicks did I get?",
    incoming=ExecutorResult(
        status="success",
        description="223 clicks recorded on 12/03/2025"
    )
)

# 3. Run Agent D
result_success = agent.run(state_success)

print("\n==============================")
print(" EXPLAINER AGENT — SUCCESS CASE")
print("==============================")
print(result_success)
print(result_success["state"])
print("Status:", result_success["state"].status)
print("Description:", result_success["state"].description)


# ---------------------------------------
# SECOND TEST — error case
# ---------------------------------------

state_error = ExplanationInput(
    user_question="how many clicks?",
    incoming=ExecutorResult(
        status="error",
        description="SQL syntax error near 'FROM'"
    )
)

result_error = agent.run(state_error)

print("\n==============================")
print(" EXPLAINER AGENT — ERROR CASE")
print("==============================")
print(result_error)
print(result_error["state"])
print("Status:", result_error["state"].status)
print("Description:", result_error["state"].description)
