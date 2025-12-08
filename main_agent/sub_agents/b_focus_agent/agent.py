from google.adk.agents import BaseAgent
from google import genai
import json
import os

from .schemas import AgentBInput, AgentBOutput


class FocusAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="b_focus_agent")

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Missing GOOGLE_API_KEY environment variable.")

        object.__setattr__(self, "client", genai.Client(api_key=api_key))

    def _normalize_state(self, state):
        """Allow RootAgent to pass dicts into FocusAgent."""
        if isinstance(state, AgentBInput):
            return state

        if isinstance(state, dict):
            return AgentBInput(
                original_question=state.get("question"),
                refined_question=state.get("refined_question"),
                missing_fields=state.get("missing_fields", []),
            )

        return AgentBInput(
            original_question=str(state),
            refined_question=None,
            missing_fields=[],
        )

    def run(self, state):
        state = self._normalize_state(state)

        original_question = state.original_question
        refined_question = getattr(state, "refined_question", None)

        prompt = f"""
You are Agent B – the Focus Agent.
(… your exact prompt …)

original_question: {original_question}
refined_question: {refined_question}
"""

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        content = (response.text or "").strip()

        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0].strip()

        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {
                "awaiting_user_input": False,
                "question_to_user": None,
                "missing_fields": [],
                "refined_question": None,
                "failed": True,
                "error_message": f"Agent returned invalid JSON: {content}",
            }

        # Validate and return as dict
        output_model = AgentBOutput(
            awaiting_user_input=parsed.get("awaiting_user_input", False),
            question_to_user=parsed.get("question_to_user"),
            missing_fields=parsed.get("missing_fields", []),
            refined_question=parsed.get("refined_question"),
            failed=parsed.get("failed", False),
            error_message=parsed.get("error_message"),
        )

        output_dict = output_model.model_dump()

        return {
            "state": output_dict,
            "should_run_focus": False,
            "should_run_executor": False,
            "should_run_explainer": False,
        }
