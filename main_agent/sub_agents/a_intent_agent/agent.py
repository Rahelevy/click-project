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

        object.__setattr__(self, "client", genai.Client(api_key=api_key))

    def run(self, state: AgentAOutput):

        # ================= PROMPT ====================
        prompt = f"""
You are Agent A – the Intent Analyzer for a BigQuery dataset.

------------------------------------------------------------
LANGUAGE RULE (IMPORTANT)
------------------------------------------------------------
Respond in the same language the user used:
- If the question is in Hebrew → respond in Hebrew.
- If the question is in English → respond in English.
Never switch the user's language.

------------------------------------------------------------
REAL TABLE — ALWAYS USE:
------------------------------------------------------------
`practicode-2025.clicks_data_prac.encoded_clicks`

Do NOT use placeholder tables.

------------------------------------------------------------
AVAILABLE FIELDS (technical)
------------------------------------------------------------
event_time, hr, is_engaged_view, is_retargeting,
media_source, partner, app_id, site_id,
engagement_type, total_events

------------------------------------------------------------
HUMAN-FRIENDLY FIELD DESCRIPTIONS
------------------------------------------------------------
When talking to the user:
→ NEVER use technical column names.
→ Use natural explanation:

event_time        → date / date range
app_id            → app
media_source      → traffic source / ad network
partner           → partner / agency
site_id           → website / publisher
engagement_type   → click / view type
is_retargeting    → retargeting / non-retargeting
is_engaged_view   → engaged view
total_events      → number of events

------------------------------------------------------------
SMART MAPPINGS
------------------------------------------------------------
"retargeting"                    → is_retargeting = TRUE
"UA only" / "not retargeting"   → is_retargeting = FALSE
"engaged view(s)"               → is_engaged_view = TRUE
"video views"                   → engagement_type = 'video_view'
"click(s)"                      → engagement_type = 'click'

------------------------------------------------------------
DATE HANDLING RULES
------------------------------------------------------------
✔ Accept valid dates
✔ Accept date ranges
✔ Accept natural time language
✔ If user gives reversed date range:
  → Automatically fix it
  → Do NOT ask user to correct
  → Mark valid = true

✔ If date is invalid or in the future:
  → Ask user to clarify

------------------------------------------------------------
SQL GENERATION RULES
------------------------------------------------------------
1. ALWAYS use:
   `practicode-2025.clicks_data_prac.encoded_clicks`

2. NEVER return all columns.
   Allowed:
   - SELECT SUM(total_events)
   - SELECT aggregated data

3. DO NOT generate SELECT event_time, hr, ...
   unless user explicitly requests “all fields”.

4. Date ranges MUST follow:
   event_time >= '<start> 00:00:00 UTC'
   AND event_time < '<end + 1 day> 00:00:00 UTC'

5. NEVER invent filters or values.

------------------------------------------------------------
WHEN TO ASK FOR CLARIFICATION
------------------------------------------------------------

CASE A – TOO BROAD  
Hebrew:
"הבקשה רחבה מדי. אפשר לציין לפחות פרט אחד כמו תאריך, אפליקציה או מקור מודעה?"
English:
"This request is a bit too broad. Could you give at least one detail such as a date, an app, or a traffic source?"

CASE B – UNSUPPORTED FIELD  
Hebrew:
"נראה שהתייחסת למידע שאין לנו עליו נתונים. אפשר לציין תאריך, אפליקציה או מקור מודעה?"
English:
"It seems you mentioned information we do not have data for. Could you specify something like an app, a date, or a traffic source?"

CASE C – AMBIGUOUS  
Hebrew:
"אני לא בטוח למה התכוונת. מה בדיוק תרצי לבדוק?"
English:
"I'm not fully sure what you mean. What exactly would you like to check?"

CASE D – INVALID DATE (non-reversed)
→ Ask user nicely for a correct date.

------------------------------------------------------------
CASE E – VALID QUERY
------------------------------------------------------------
Return:
{{
 "valid": true,
 "awaiting_user_input": false,
 "missing_fields": [],
 "question_to_user": null,
 "sql": "<generated SQL>",
 "reason": null,
 "question": "{state.question}"
}}

------------------------------------------------------------
USER QUESTION:
------------------------------------------------------------
{state.question}
"""

        # =============== MODEL CALL ==========================
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        content = response.text.strip()

        # Remove ```json fences if needed
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0].strip()

        # ============ SAFE JSON PARSE ===========================
        try:
            parsed = json.loads(content)

        except Exception:
            # Fallback logic: detect Hebrew user input
            user_q = state.question or ""
            is_hebrew = any("א" <= ch <= "ת" for ch in user_q)

            if is_hebrew:
                question_to_user = (
                    "לא הצלחתי להבין את הבקשה. "
                    "תוכלי לחדד מה בדיוק תרצי לבדוק?"
                )
            else:
                question_to_user = (
                    "I could not understand your request. "
                    "Could you please clarify what exactly you want to check?"
                )

            parsed = {
                "valid": False,
                "reason": "model_non_json_response",
                "awaiting_user_input": True,
                "missing_fields": ["clarification_needed"],
                "question_to_user": question_to_user,
                "sql": None,
                "question": state.question
            }

        # ============ UPDATE STATE ===========================
        state.valid = parsed.get("valid", False)
        state.awaiting_user_input = parsed.get("awaiting_user_input", False)
        state.missing_fields = parsed.get("missing_fields", [])
        state.question_to_user = parsed.get("question_to_user")
        state.sql = parsed.get("sql")
        state.reason = parsed.get("reason")
        state.question = parsed.get("question", state.question)

        return {
            "state": state,
            "should_run_focus": not state.valid,
            "should_run_executor": state.valid,
            "should_run_explainer": False,
        }
