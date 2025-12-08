import logging
logging.basicConfig(level=logging.DEBUG, force=True)
logger = logging.getLogger("root_agent")
logger.debug("🔥 ROOT AGENT FILE LOADED")

from typing import AsyncGenerator, Dict, Any
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai.types import Content, Part

from main_agent.sub_agents.a_intent_agent.agent import IntentAgent
from main_agent.sub_agents.b_focus_agent.agent import FocusAgent
from main_agent.sub_agents.c_executor_agent.agent import ExecutorAgent
from main_agent.sub_agents.d_explanation_agent.agent import ExplainerAgent

from main_agent.sub_agents.d_explanation_agent.schemas import (
    ExplanationInput,
    ExecutorResult,
)

# -----------------------------------------------------
# Root Agent
# -----------------------------------------------------
class RootAgent(BaseAgent):

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    def __repr__(self):
        return f"RootAgent(name={self.name})"

    def __init__(self, intent_agent, focus_agent, executor_agent, explainer_agent):
        super().__init__(
            name="main_agent_root",
            intent_agent=intent_agent,
            focus_agent=focus_agent,
            executor_agent=executor_agent,
            explainer_agent=explainer_agent,
            sub_agents=[intent_agent, focus_agent, executor_agent, explainer_agent],
        )

    # -----------------------------------------------------
    # Main Pipeline
    # -----------------------------------------------------
    def run_pipeline(self, ctx, session_state: Dict[str, Any]) -> Dict[str, Any]:

        logger.debug(f"[Root] ctx.user_content = {ctx.user_content}")
        logger.debug(f"[Root] session_state keys = {list(session_state.keys())}")

        # -----------------------------------------------------
        # 1) Intent Agent - First pass
        # -----------------------------------------------------
        a1 = self.intent_agent.run(ctx)
        intent_state = a1["state"]     # always a dict
        logger.debug(f"[Root] Intent-1 output = {intent_state}")

        if intent_state.get("valid"):
            # SQL is already ready
            final_intent = intent_state

        else:
            # -----------------------------------------------------
            # 2) Focus Agent
            # -----------------------------------------------------
            b = self.focus_agent.run(intent_state)
            focus_state = b["state"]
            logger.debug(f"[Root] Focus output = {focus_state}")

            # Case A — Focus requires user clarification
            if focus_state.get("awaiting_user_input"):
                q = focus_state.get("question_to_user") or "Can you clarify your question?"
                return {
                    "stage": "awaiting_user_input",
                    "answer": q,
                    "state": focus_state,
                }

            # Case B — Focus refined the question → run Intent again
            if focus_state.get("refined_question"):
                refined_q = focus_state["refined_question"]
                logger.debug(f"[Root] Intent-2 with refined question = {refined_q}")

                a2 = self.intent_agent.run({"question": refined_q})
                intent2_state = a2["state"]
                logger.debug(f"[Root] Intent-2 output = {intent2_state}")

                if intent2_state.get("awaiting_user_input"):
                    q = intent2_state.get("question_to_user")
                    return {
                        "stage": "awaiting_user_input",
                        "answer": q,
                        "state": intent2_state,
                    }

                final_intent = intent2_state

            else:
                # No refinement → use initial intent_state
                final_intent = intent_state

        # -----------------------------------------------------
        # 3) EXECUTOR (SQL execution)
        # -----------------------------------------------------
        executor_input = {
            "user_question": final_intent.get("question"),
            "sql": final_intent.get("sql"),
        }

        c = self.executor_agent.run(executor_input)
        exec_state = c["state"]   # dict from AgentCOutput
        logger.debug(f"[Root] Executor output = {exec_state}")

        # -----------------------------------------------------
        # 4) EXPLAINER
        # -----------------------------------------------------
        explain_input = ExplanationInput(
            user_question=exec_state["user_question"],
            incoming=ExecutorResult(
                status=exec_state["incoming"]["status"],
                description=exec_state["incoming"]["description"],
            ),
            db_result=exec_state.get("db_result"),
        )

        d = self.explainer_agent.run(explain_input)
        explain_state = d["state"]   # Pydantic model
        logger.debug(f"[Root] Explainer output = {explain_state}")

        # Convert Pydantic → dict to store in ADK session safely
        if hasattr(explain_state, "model_dump"):
            explain_state = explain_state.model_dump()

        return {
            "stage": "done",
            "answer": explain_state.get("description", ""),
            "state": explain_state,
        }

    # -----------------------------------------------------
    # ADK Async Wrapper
    # -----------------------------------------------------
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:

        session_state = ctx.session.state.get("root_state", {})

        logger.debug(f"[Root] Async start: {ctx.user_content}")

        result = self.run_pipeline(ctx, session_state)
        logger.debug(f"[Root] Final Output = stage={result['stage']} answer={result['answer']}")

        # Update session
        actions = EventActions(
            state_delta={
                "root_state": result["state"],
                "stage": result["stage"],
            }
        )

        msg = Content(
            role="assistant",
            parts=[Part(text=result.get("answer", "No answer returned."))],
        )

        yield Event(
            author=self.name,
            content=msg,
            actions=actions,
        )


root_agent = RootAgent(
    intent_agent=IntentAgent(),
    focus_agent=FocusAgent(),
    executor_agent=ExecutorAgent(),
    explainer_agent=ExplainerAgent(),
)
