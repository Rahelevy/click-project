from google.adk.agents import BaseAgent
from google import genai
import json
import os
from dotenv import load_dotenv

from .schemas import ExplanationInput, ExplanationOutput


EXPLANATION_SYSTEM_PROMPT = """
You are AGENT D — the final layer before answering the end user.

INPUT YOU RECEIVE:
- user_question: the user's original natural-language question.
- incoming: a JSON object from the EXECUTOR:
    {
        "status": "success" or "error",
        "description": "<technical info or raw extracted data>"
    }

YOUR JOB:
Transform the EXECUTOR's description into a friendly human explanation.

ABSOLUTE RULES:
1. Always respond in the same language as the user_question (Hebrew or English).
2. Always return JSON ONLY in the following format:
    {
      "status": "<success/error>",
      "description": "<friendly explanation>"
    }
3. Never invent details. Never output SQL.

---------------------------------------------------------
SUCCESS HANDLING (incoming.status == "success")
---------------------------------------------------------
CRITICAL: If you receive an "ACTUAL DATA" section in the input, you MUST display it as a table.
Never just say "We found N rows" without showing the data.

The result may be one of these forms:
A) A single aggregated number (count/sum of clicks).
B) ACTUAL DATA section with rows of data.
C) Plain text description only (no data).

You must detect which case it is and respond accordingly.

### CASE A — SINGLE NUMBER / COUNT (no ACTUAL DATA section)
If incoming.description represents a number and there is NO "ACTUAL DATA" section:
- Explain naturally and warmly in the user's language.
- If the number is 0:
    Hebrew: "לא נמצאו קליקים עבור הבקשה שלך."
    English: "No clicks were found for your request."
- Example: "We found 2,345 clicks for your request."

### CASE B — ACTUAL DATA PROVIDED (most common)
If you see an "ACTUAL DATA" section with JSON array of objects:
MANDATORY: You MUST build and display a Markdown table.
1) Parse the JSON list of objects.
2) Extract all column names from all rows (union of keys).
3) Build a clean Markdown table inside description.

TABLE RULES:
- Collect column names from ALL rows (union of keys). 
  If some rows miss a column, leave that cell blank.
- Keep stable, readable order of columns (start with the first row’s keys, then add new ones).
- If the table is VERY LARGE:
  - Show only the first 20 rows.
  - Add a short note that only first 20 rows are displayed.

- Always put a short title above the table, same language as user:
  Hebrew: "סיכום קליקים:"
  English: "Click summary:"

- Always add a blank line before and after the table.

- Format exactly like:
סיכום קליקים:

| Col 1 | Col 2 |
|-------|-------|
| v1    | v2    |
| v1    | v2    |

STRICT TABLE OUTPUT (MUST FOLLOW EXACTLY):
- The Markdown table MUST have:
  1) Header row
  2) Separator row with EXACTLY one "---" cell per column (same column count)
  3) Data rows
- Do NOT try to align widths with many dashes. Always use exactly:
  |---|---|---|  (matching number of columns)

DATE FORMATTING:
- If you see a date in format YYYY-MM-DD, and the user is Hebrew,
  convert it to DD/MM/YYYY in the table.

FINAL FORM:
- The description MUST be exactly:

\u200Fסיכום קליקים:

| <col1> | <col2> |
|---|---|
| v1 | v2 |
| v1 | v2 |

- Always end the description with a newline after the last row.

HEBREW TABLE SPECIAL RULES:
- Translate common column names to Hebrew if needed:
  date/event_time/day -> "תאריך"
  clicks/count/total -> "מספר קליקים" / "כמות"
  app_id -> "App ID"
  media_source -> "מקור מדיה"
  partner -> "שותף"
  site_id -> "Site ID"
  engagement_type -> "סוג מעורבות"
  country -> "מדינה"
  platform -> "פלטפורמה"
  device -> "מכשיר"
  hour -> "שעה"
- If a column is unknown, keep it as-is.
- If a column is "date", format values as DD/MM/YYYY for Hebrew users.

### IMPORTANT:
- Never output both explanation text and raw JSON.
- The final JSON MUST always match ExplanationOutput exactly.

---------------------------------------------------------
ERROR HANDLING (incoming.status == "error")
---------------------------------------------------------
Even though RootAgent should not send errors here, if you ever see error:
- Explain gently, clearly, in same language.
- Give helpful guidance.
- No raw stack traces unless absolutely necessary.
- No tables.

Return JSON ONLY.
"""




class ExplainerAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="explainer_agent")

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
        if not api_key:
            raise ValueError("Missing GOOGLE_API_KEY environment variable.")

        # Gemini client
        object.__setattr__(self, "client", genai.Client(api_key=api_key))

    def run(self, state):
        # Handle both Pydantic model and dict inputs
        if isinstance(state, dict):
            user_question = state.get("user_question", "")
            incoming = state.get("incoming", {})
            db_result = state.get("db_result")
            sql = None  # do not expose SQL in user-visible prompt
            if isinstance(incoming, dict):
                incoming_json = json.dumps(incoming)
            else:
                # incoming is a Pydantic model
                incoming_json = incoming.model_dump_json()
        else:
            # state is ExplanationInput Pydantic model
            user_question = state.user_question
            incoming_json = state.incoming.model_dump_json()
            db_result = state.db_result
            sql = None  # do not expose SQL in user-visible prompt

        # If we have actual row data, add it to the prompt
        if db_result and isinstance(db_result, list) and len(db_result) > 0:
            db_result_json = json.dumps(db_result, ensure_ascii=False, indent=2)
            data_section = f"""
--------------------
ACTUAL DATA (display this as a table):
--------------------
{db_result_json}
"""
        else:
            data_section = ""

        # Build instruction + input
        prompt = f"""
{EXPLANATION_SYSTEM_PROMPT}

--------------------
USER QUESTION:
--------------------
{user_question}

--------------------
EXECUTOR RESULT:
--------------------
{incoming_json}
{data_section}
"""

        # Call Gemini
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        # Extract text
        content = (response.text or "").strip()

        # Strip code fences if the LLM returns ```json ... ```
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0].strip()

        # Parse JSON
        try:
            parsed = json.loads(content)
        except Exception:
            raise ValueError(f"Agent D returned invalid JSON:\n{content}")

        # Build ExplanationOutput state
        # Handle both dict and pydantic model inputs
        default_status = state.incoming.status if hasattr(state, 'incoming') else state.get('incoming', {}).get('status', 'unknown')
        description = parsed.get("description", "")
        
        # Append SQL query for debugging if available
        if sql:
            description += f"\n\n---\n**SQL Query:**\n```sql\n{sql}\n```"
        
        output = ExplanationOutput(
            status=parsed.get("status", default_status),
            description=description
        )

        # Return updated state to RootAgent
        return {
            "state": output,
            "should_run_focus": False,
            "should_run_executor": False,
            "should_run_explainer": False,  # last agent
        }
