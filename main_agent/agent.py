from google.adk.agents import SequentialAgent, LoopAgent

from .sub_agents.a_intent_agent.agent import intent_agent
from .sub_agents.b_focus_agent.agent import focus_agent
from .sub_agents.c_executor_agent.agent import executor_agent
from .sub_agents.d_explanation_agent.agent import explainer_agent

# LOOP A <-> B
refinement_loop = LoopAgent(
    name="refinement_loop",
    max_iterations=1,
    sub_agents=[
        intent_agent,   # FIRST → checks validity
        focus_agent,    # SECOND → only called if A returns needs_focus=true
    ],
    description="Loop between Agent A and B until the question becomes valid."
)

root_agent = SequentialAgent(
    name="main_agent",
    description="Full pipeline",
    sub_agents=[
        refinement_loop,   # Step 1: Loop until valid
        executor_agent,    # Step 2: execute SQL
        explainer_agent,   # Step 3: explain results
    ],
)
