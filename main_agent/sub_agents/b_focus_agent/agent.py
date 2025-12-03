# from google.adk.agents import Agent
# from .schemas import AgentBInput, AgentBOutput
# from .tools import exit_loop


# # לכתוב לו שיחזיר הודעת שגיאה אם משהו משתבש 


# focus_agent = Agent(
#     name="b_focus_agent",
#     model="gemini-2.5-flash",
#     description="Focus Agent – helps user add missing filter fields for SQL validity.",
#     instruction="""
# You are Agent B – the Focus Agent.

# Your tasks:
# 1. Call detect_missing_fields(original_question) to determine which filter fields are missing.
# 2. Use:
#    - awaiting_user_input
#    - missing_fields
#    - question_to_user
#    - refined_question
#    according to the schema AgentBOutput.

# ---------------------------------------------------------
# CASE 1 — missing_fields IS EMPTY (already enough filters)
# ---------------------------------------------------------
# - The question already has enough filters.
# - You MUST stop the refinement loop now.
# - Return exactly:
# {
#   "awaiting_user_input": false,
#   "refined_question": "<refined_question>",
#   "missing_fields": [],
#   "failed": false,
#   "error_message": null
# }
# - AFTER returning this JSON, you MUST call exit_loop() so the LoopAgent stops.

# ---------------------------------------------------------
# CASE 2 — missing_fields NOT EMPTY (still missing info)
# ---------------------------------------------------------
# - The question does NOT have enough filters.
# - You must ask the user for ONE missing field.
# - Do NOT invent values.

# Return exactly:
# {
#   "awaiting_user_input": true,
#   "question_to_user": "<your short clarification question>",
#   "missing_fields": ["field1", "field2"],
#   "refined_question": null,
#   "failed": false,
#   "error_message": null
# }
# - AFTER returning this JSON, you MUST call exit_loop() so the LoopAgent stops and waits for the user.

# RULES:
# - Never use clarification_question (only question_to_user).
# - Never return both refined_question AND question_to_user.
# - Never generate or explain SQL.
# - Keep clarification questions short and simple.
# - missing_fields must always reflect the fields that are still absent.
# """,
#     input_schema=AgentBInput,
#     output_schema=AgentBOutput,
#     tools=[exit_loop],
# )


from google.adk.agents import BaseAgent
from google import genai
import json
import os

from .schemas import AgentBInput, AgentBOutput
from .tools import exit_loop


class FocusAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="b_focus_agent")

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Missing GOOGLE_API_KEY environment variable.")

        # Attach Gemini client safely
        object.__setattr__(self, "client", genai.Client(api_key=api_key))


    def run(self, state: AgentBInput):
        """
        Focus agent: helps user add missing filter fields.
        Returns AgentBOutput-compatible JSON and stops loop via exit_loop().
        If parsing fails, returns failed=true + error_message.
        """

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
- The question already has enough filters.
- You MUST stop the refinement loop now.
- Return exactly:
{{
  "awaiting_user_input": false,
  "refined_question": "<refined_question>",
  "missing_fields": [],
  "failed": false,
  "error_message": null
}}
- AFTER returning this JSON, you MUST call exit_loop() so the LoopAgent stops.

---------------------------------------------------------
CASE 2 — missing_fields NOT EMPTY (still missing info)
---------------------------------------------------------
- The question does NOT have enough filters.
- You must ask the user for ONE missing field.
- Do NOT invent values.

Return exactly:
{{
  "awaiting_user_input": true,
  "question_to_user": "<your short clarification question>",
  "missing_fields": ["field1", "field2"],
  "refined_question": null,
  "failed": false,
  "error_message": null
}}
- AFTER returning this JSON, you MUST call exit_loop() so the LoopAgent stops and waits for the user.

RULES:
- Never use clarification_question (only question_to_user).
- Never return both refined_question AND question_to_user.
- Never generate or explain SQL.
- Keep clarification questions short and simple.
- missing_fields must always reflect the fields that are still absent.
- ALWAYS return JSON ONLY matching AgentBOutput exactly.

--------------------------------
INPUT:
--------------------------------
original_question: {state.original_question}
refined_question: {getattr(state, "refined_question", None)}
"""

        # NEW GENERATE CALL (correct for new SDK)
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        content = (response.text or "").strip()

        # Strip Markdown fences
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0].strip()

        try:
            parsed = json.loads(content)
        except Exception:
            # כמו שהערת ב-TODO: לא לקרוס אלא להחזיר שגיאה בתוך הסכמה
            parsed = {
                "awaiting_user_input": False,
                "question_to_user": None,
                "missing_fields": [],
                "refined_question": None,
                "failed": True,
                "error_message": f"Agent returned invalid JSON: {content}",
            }

        # לבנות אובייקט Output תקין לפי הסכמה
        output = AgentBOutput(
            awaiting_user_input=parsed.get("awaiting_user_input", False),
            question_to_user=parsed.get("question_to_user"),
            missing_fields=parsed.get("missing_fields", []),
            refined_question=parsed.get("refined_question"),
            failed=parsed.get("failed", False),
            error_message=parsed.get("error_message"),
        )

        # חשוב: לעצור את הלופ כמו tools=[exit_loop] ב-Agent(...)
        try:
            exit_loop()
        except TypeError:
            # manual run: no ADK tool_context
            pass

        return {
            "state": output,
            # אם את רוצה flags אחרים פה — תגידי, אני אתאים.
            "should_run_focus": False,
            "should_run_executor": False,
            "should_run_explainer": False,
        }
