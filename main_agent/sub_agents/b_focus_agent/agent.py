from google.adk.agents import BaseAgent
from google import genai
import json
import os
import re
from dotenv import load_dotenv

from .schemas import AgentBInput, AgentBOutput


class FocusAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="b_focus_agent")

        # Load .env from main_agent/.env explicitly (fallback to default search)
        _env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        try:
            if os.path.exists(_env_path):
                load_dotenv(_env_path)
            else:
                load_dotenv()
        except Exception:
            load_dotenv()

        api_key = os.getenv("GOOGLE_API_KEY")
        # API key is optional - can use service account credentials via GOOGLE_APPLICATION_CREDENTIALS
        if api_key:
            object.__setattr__(self, "client", genai.Client(api_key=api_key))
        else:
            # Use service account credentials with Vertex AI
            object.__setattr__(self, "client", genai.Client(
                vertexai=True,
                project="practicode-2025",
                location="us-central1"
            ))

    def _normalize_state(self, state):
        """Allow RootAgent to pass dicts into FocusAgent."""

        # Case 1: already AgentBInput
        if isinstance(state, AgentBInput):
            return state

        # Case 2: Root passed dict  (זה בדיוק מה ש-Root עושה)
        if isinstance(state, dict):
            return AgentBInput(
                original_question=state.get("question", ""),
                reason=state.get("reason") or "missing_filters",   # ✅ תיקון כאן
                missing_fields=state.get("missing_fields", []),
                refined_question=state.get("refined_question"),
            )

        # Case 3: fallback object
        return AgentBInput(
            original_question=getattr(state, "question", None) or str(state),
            reason=getattr(state, "reason", None) or "missing_filters",  # ✅ אותו תיקון
            missing_fields=getattr(state, "missing_fields", None) or [],
            refined_question=getattr(state, "refined_question", None),
        )

    def run(self, state):
        state = self._normalize_state(state)

        original_question = state.original_question
        refined_question = state.refined_question
        missing_fields = state.missing_fields
        reason = state.reason

        # Language detection used throughout the handler
        is_hebrew = any("א" <= ch <= "ת" for ch in (original_question or ""))

        # Heuristic handling: ask for ONE missing field deterministically.
        # Only skip LLM when both app_id and date exist.
        def _has_iso_date(txt: str) -> bool:
            return bool(re.search(r"\b\d{4}-\d{2}-\d{2}\b", txt or ""))

        def _has_any_date(txt: str) -> bool:
            if _has_iso_date(txt):
                return True
            return bool(re.search(r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\b", txt or ""))

        def _has_app_id(txt: str) -> bool:
            return bool(re.search(r"\bapp[_ ]?id[_ ]?(\d+)\b|\bapp_id_\d+\b", txt or "", flags=re.IGNORECASE))
        has_date = _has_any_date(original_question)
        has_app = _has_app_id(original_question)

        # Language-aware messages
        ask_date_he = "מה התאריך או טווח התאריכים הרצוי?"
        ask_date_en = "What date or date range would you like?"
        ask_app_he = "מהו מזהה האפליקציה (בפורמט app_id_<מספר>)?"
        ask_app_en = "What is the app id (format app_id_<number>)?"

        # Additional detectors for other allowed fields
        def _has_media_source(txt: str) -> bool:
            t = (txt or "").lower()
            tokens = ["media source", "media_source", "source ", "ad network", "network"]
            heb = ["מקור", "מקור תנועה", "מקור פרסום"]
            return any(tok in t for tok in tokens) or any(h in txt for h in heb)

        def _has_partner(txt: str) -> bool:
            t = (txt or "").lower()
            tokens = ["partner", "agency"]
            heb = ["שותף", "סוכנות"]
            return any(tok in t for tok in tokens) or any(h in txt for h in heb)

        def _has_site_id(txt: str) -> bool:
            t = (txt or "").lower()
            tokens = ["site id", "site_id", "publisher"]
            heb = ["אתר", "פאבלישר"]
            return any(tok in t for tok in tokens) or any(h in txt for h in heb)

        has_source = _has_media_source(original_question)
        has_partner = _has_partner(original_question)
        has_site = _has_site_id(original_question)

        # If none of the supported fields are present, ask the user to pick one field to narrow by.
        if not (has_app or has_date or has_source or has_partner or has_site):
            if is_hebrew:
                q_to_user = (
                    "על איזה שדה תרצה/תרצי למקד? אפשר לבחור אחד: "
                    "אפליקציה (app_id), מקור תנועה (media_source), שותף (partner), אתר (site_id), תאריך או טווח תאריכים."
                )
            else:
                q_to_user = (
                    "Which single field would you like to narrow by? "
                    "You may pick one: app (app_id), media source, partner, site id, or a date/date range."
                )

            output_model = AgentBOutput(
                awaiting_user_input=True,
                question_to_user=q_to_user,
                missing_fields=["app_id", "media_source", "partner", "site_id", "date"],
                refined_question=None,
                failed=False,
                error_message=None,
            )
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

        # If at least one field is present, proceed without further clarification.
        output_model = AgentBOutput(
            awaiting_user_input=False,
            question_to_user=None,
            missing_fields=[],
            refined_question=original_question,
            failed=False,
            error_message=None,
        )
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

        # >>> ADDED: language rule for prompt
        lang_rule = (
            "Respond in Hebrew, because the user's question is in Hebrew."
            if is_hebrew else
            "Respond in English, because the user's question is in English."
        )

        prompt = f"""
You are Agent B – the Focus Agent.

LANGUAGE RULE (IMPORTANT):
{lang_rule}
Never switch the user's language.

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

original_question: {original_question}
refined_question: {refined_question}
missing_fields: {missing_fields}
reason: {reason}
"""

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
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