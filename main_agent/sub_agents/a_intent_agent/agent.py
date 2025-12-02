from google.adk.agents import BaseAgent
from google import genai
import json
import os

from .schemas import AgentAOutput


class IntentAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="intent_agent")

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Missing GOOGLE_API_KEY environment variable.")

        # Attach Gemini client safely
        object.__setattr__(self, "client", genai.Client(api_key=api_key))


    def run(self, state: AgentAOutput):

        prompt = f"""
You are Agent A – the Intent Analyzer.

Your tasks:
1. Read and understand the user's free-text question.
2. Detect whether the question contains at least one concrete filter with a value.
3. Update the context state accordingly:
  - awaiting_user_input
  - missing_fields
  - question_to_user

VALID FILTER EXAMPLES:
app_id, media_source, partner, site_id, engagement_type, 
campaign_id, country, platform, device, hour, event_time, date, date range.

Forbidden operations: DELETE, DROP, UPDATE, INSERT, ALTER, TRUNCATE.

--------------------------------
CASE 1 — MISSING INFORMATION
--------------------------------
If the question contains ZERO valid filters:
Return JSON ONLY in this shape:

{{
  "valid": false,
  "awaiting_user_input": true,
  "missing_fields": ["<field_name>"],
  "question_to_user": "<ask the user for missing info>",
  "sql": null,
  "question": "{state.question}"
}}

Rules for CASE 1:
- Do NOT invent values
- Do NOT generate SQL
- The user must provide missing fields

--------------------------------
CASE 2 — ENOUGH INFORMATION
--------------------------------
If at least ONE valid filter exists:
Return JSON ONLY in this shape:

{{
  "valid": true,
  "awaiting_user_input": false,
  "missing_fields": [],
  "question_to_user": null,
  "sql": "<generated SQL>",
  "question": "{state.question}"
}}

Rules for CASE 2:
- SQL MUST be syntactically correct
- SQL MUST NOT include forbidden operations
- SQL MUST reflect the user's actual filters
- Never invent values
- Never refine or reinterpret the question

--------------------------------
IMPORTANT RULES
--------------------------------
- NEVER refine the question.
- NEVER invent missing information.
- NEVER hallucinate filters.
- ALWAYS return JSON ONLY.
- ALWAYS match AgentAOutput exactly.

--------------------------------
USER QUESTION:
--------------------------------
{state.question}
"""

        # NEW GENERATE CALL (correct for new SDK)
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        content = response.text.strip()
        # Strip Markdown fences
        if content.startswith("```"):
            # remove first line (``` or ```json)
            content = content.split("\n", 1)[1]
            # remove last line (```)
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0].strip()

        try:
            parsed = json.loads(content)
        except Exception:
            raise ValueError(f"Agent returned invalid JSON:\n{content}")

        state.valid = parsed.get("valid", False)
        state.awaiting_user_input = parsed.get("awaiting_user_input", False)
        state.missing_fields = parsed.get("missing_fields", [])
        state.question_to_user = parsed.get("question_to_user")
        state.sql = parsed.get("sql")
        state.question = parsed.get("question", state.question)

        return {
            "state": state,
            "should_run_focus": not state.valid,
            "should_run_executor": state.valid,
            "should_run_explainer": False,
        }
