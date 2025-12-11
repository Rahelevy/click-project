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

        # Case 1: already AgentBInput
        if isinstance(state, AgentBInput):
            return state

        # Case 2: Root passed dict  (זה בדיוק מה ש-Root עושה)
        if isinstance(state, dict):
            return AgentBInput(
                original_question=state.get("question", ""),
                reason=state.get("reason", "missing_filters"),
                missing_fields=state.get("missing_fields", []),
                refined_question=state.get("refined_question"),
            )

        # Case 3: fallback object
        return AgentBInput(
            original_question=getattr(state, "question", None) or str(state),
            reason=getattr(state, "reason", None) or "missing_filters",
            missing_fields=getattr(state, "missing_fields", None) or [],
            refined_question=getattr(state, "refined_question", None),
        )

    def run(self, state):
        state = self._normalize_state(state)

        original_question = state.original_question
        refined_question = state.refined_question
        missing_fields = state.missing_fields
        reason = state.reason

        prompt = f"""
You are Agent B – the Focus Agent.

Your tasks:
1. Call detect_missing_fields(original_question) to determine which filter fields are missing.
2. Use:
   - awaiting_user_input
   - missing_fields
   - question_to_user
   - refined_question
   according to the schema AgentBOutput.

---------------------------------------------------------
CASE 1 — missing_fields IS EMPTY (already enough filters)
---------------------------------------------------------
The question already has enough filters.
You MUST stop the refinement loop now.
Return exactly:
{{
  "awaiting_user_input": false,
  "refined_question": "<refined_question>",
  "missing_fields": [],
  "failed": false,
  "error_message": null
}}

---------------------------------------------------------
CASE 2 — missing_fields NOT EMPTY (still missing info)
---------------------------------------------------------
The question does NOT have enough filters.
You must ask the user for ONE missing field.
Do NOT invent values.

Return exactly:
{{
  "awaiting_user_input": true,
  "question_to_user": "<your short clarification question>",
  "missing_fields": ["field1", "field2"],
  "refined_question": null,
  "failed": false,
  "error_message": null
}}

RULES:
Never use clarification_question (only question_to_user).
Never return both refined_question AND question_to_user.
Never generate or explain SQL.
Keep clarification questions short and simple.
missing_fields must always reflect the fields that are still absent.
ALWAYS return JSON ONLY matching AgentBOutput exactly.

--------------------------------
INPUT:
--------------------------------

original_question: {original_question}
refined_question: {refined_question}
missing_fields: {missing_fields}
reason: {reason}
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

        output_model = AgentBOutput(
            awaiting_user_input=parsed.get("awaiting_user_input", False),
            question_to_user=parsed.get("question_to_user"),
            missing_fields=parsed.get("missing_fields", []),
            refined_question=parsed.get("refined_question"),
            failed=parsed.get("failed", False),
            error_message=parsed.get("error_message"),
        )

        # Pydantic v2 -> model_dump, v1 -> dict
        output_dict = (
            output_model.model_dump()
            if hasattr(output_model, "model_dump")
            else output_model.dict()
        )

        return {
            "state": output_dict,
            "should_run_focus": False,
            "should_run_executor": False,
            "should_run_explainer": False,
        }