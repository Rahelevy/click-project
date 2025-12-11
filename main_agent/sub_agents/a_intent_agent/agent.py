from datetime import date

import logging
logger = logging.getLogger("intent")
logger.debug("🔥 IntentAgent loaded")

from multiprocessing.util import debug
from google.adk.agents import BaseAgent
from google import genai
import json
import os
import re

from .schemas import AgentAOutput
from dotenv import load_dotenv

load_dotenv()  # <-- FORCE LOAD .env


class IntentAgent(BaseAgent):
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    def __repr__(self) -> str:
        return f"IntentAgent(name={self.name})"

    def __init__(self):
        super().__init__(name="intent_agent")

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Missing GOOGLE_API_KEY environment variable.")

        object.__setattr__(self, "client", genai.Client(api_key=api_key))

    # =========================
    # STATIC HELPERS FROM FRIEND
    # =========================

    @staticmethod
    def _is_hebrew(text: str) -> bool:
        return any("א" <= ch <= "ת" for ch in (text or ""))

    @staticmethod
    def _has_filter_hint(text: str) -> bool:
        if not text:
            return False

        t = text.lower()

        hints = [
            "app id", "appid", "app_id", "app ",
            "media source", "media_source", "source ",
            "partner", "agency",
            "site id", "site_id", "publisher",
            "date", "day", "hour", "time",
            "retargeting", "re-engaged", "installed before",
            "click", "view"
        ]

        heb_hints = [
            "אפליקציה", "מקור פרסום", "מקור התנועה", "שותף",
            "פאבלישר", "אתר", "תאריך", "יום", "שעה", "ריטרגטינג",
            "התקינו בעבר", "משתמשים חוזרים"
        ]

        numeric_patterns = [
            r"media\s*source\s*\d+",
            r"site\s*id\s*\d+",
            r"partner\s*\d+",
            r"app\s*id\s*\d+",
        ]

        for p in numeric_patterns:
            if re.search(p, t):
                return True

        return any(h in t for h in hints) or any(h in text for h in heb_hints)

    @staticmethod
    def _looks_too_broad(text: str) -> bool:
        if not text:
            return True

        t = text.lower().strip()

        broad_patterns = [
            r"\ball the data\b",
            r"\ball data\b",
            r"\beverything\b",
        ]
        heb_broad = [
            "כל הדאטה",
            "כל המידע",
            "תן לי הכל",
            "תני לי הכל",
        ]

        if any(p in t for p in heb_broad):
            return True
        if any(re.search(p, t) for p in broad_patterns):
            return True

        if not IntentAgent._has_filter_hint(text):
            return True

        return False

    # =============================
    # MAIN RUN (YOUR ORIGINAL LOGIC)
    # =============================

    def run(self, state):
        logger.debug(f"[IntentAgent] Running with state= {state}")

        # Extract user question safely from ctx / dict / pydantic / fallback string
        try:
            user_question = state.user_content.parts[0].text
        except Exception:
            if isinstance(state, dict):
                user_question = state.get("question")
            else:
                user_question = getattr(state, "question", None) or str(state)

        # Edge case: no question extracted  (A מטפל בזה לבד)
        if not user_question:
            is_hebrew = self._is_hebrew(str(state))
            clean = {
                "valid": False,
                "awaiting_user_input": True,   # A כן מבקש ניסוח מחדש
                "missing_fields": ["question"],
                "sql": None,
                "reason": "missing_question",
                "question": "",
            }
            return {
                "state": clean,
                "should_run_focus": False,     # לא שולחים ל-B
                "should_run_executor": False,
                "should_run_explainer": False,
            }

        # Too broad / missing filters → send to Focus
        if self._looks_too_broad(user_question):

            clean = {
                "valid": False,
                "awaiting_user_input": False,   # A לא שואל; B ישאל
                "missing_fields": ["filter_needed"],
                "sql": None,
                "reason": "too_broad",
                "question": user_question,
            }

            return {
                "state": clean,
                "should_run_focus": True,
                "should_run_executor": False,
                "should_run_explainer": False,
            }

        # ---- BUILD YOUR FULL PROMPT (UPDATED TO REMOVE question_to_user) ----
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

ENGAGEMENT TYPE RULES
------------------------------------------------------------
In this dataset, the column engagement_type always has the same value:
  'engagement_type_1'.

Therefore:
- You MUST NOT add any WHERE condition on engagement_type.
- You MAY include engagement_type in the SELECT list when returning rows,
  but do not use it to filter the data.

------------------------------------------------------------
RETARGETING SEMANTIC RULES
------------------------------------------------------------
If the user describes events involving users who have already installed the app,
you MUST treat it as retargeting = TRUE.

Trigger phrases include:
- "users who already installed"
- "people who installed before"
- "returning users" / "re-engaged users"
- "users who came back"
- "מי שכבר התקין"
- "משתמשים שהתקינו בעבר"
- "משתמשים חוזרים"
- "מי שחזר"
- "התקנה בעבר"

This is equivalent to:
is_retargeting = TRUE

Even if the user did NOT explicitly use the word "retargeting".

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
  → Mark valid = false
  → awaiting_user_input = false
  → missing_fields should include "date"
  → Do NOT ask the user directly (Agent B will ask)

------------------------------------------------------------
DATE FORMAT RULE (MM-DD-YYYY)
------------------------------------------------------------
If the user writes a date like "10-24-2025", always interpret it as:

  MM-DD-YYYY → Month-Day-Year

So:
  "10-24-2025" → October 24, 2025

Compare this against the *real current date*.

------------------------------------------------------------
DATE FILTERING RULE (IMPORTANT — USE PARTITIONS!)
------------------------------------------------------------
The table practicode-2025.clicks_data_prac.encoded_clicks is
partitioned by DATE(event_time). Therefore:

YOU MUST ALWAYS FILTER DATES USING:

    DATE(event_time)

and NEVER compare raw timestamps unless the user explicitly asks.

Correct usage examples:
  DATE(event_time) = "2025-10-24"
  DATE(event_time) BETWEEN "2025-10-24" AND "2025-10-26"

------------------------------------------------------------
SQL GENERATION RULES
------------------------------------------------------------
1. ALWAYS use:
   `practicode-2025.clicks_data_prac.encoded_clicks`

2. NEVER return all columns by default.

3. DO NOT generate SELECT event_time, hr, ...
   unless user explicitly requests “all fields” or a non-aggregated list.

4. NEVER invent filters or values.

------------------------------------------------------------
APP_ID FORMAT RULES
------------------------------------------------------------
The dataset uses synthetic app IDs in the form "app_id_<number>"
(e.g. "app_id_1", "app_id_2", "app_id_20").

1) If the user provides an app id as a plain number, such as:
   - "app id = 2"
   - "app id 2"
   - "app_id 3"
   - "app 10"
   - "appid=5"

   YOU MUST convert it to the correct string format in SQL:

   app_id = "app_id_<number>"

------------------------------------------------------------
MEDIA SOURCE / PARTNER / SITE ID RULES
------------------------------------------------------------
Same as original rules:
- media_source_<number>
- partner_<number>
- site_id_<number>
Convert plain numbers accordingly.

------------------------------------------------------------
COUNT vs SUM RULES
------------------------------------------------------------
(keep your original rules...)

------------------------------------------------------------
OUTPUT FORMAT (NO question_to_user)
------------------------------------------------------------
Return JSON ONLY matching AgentAOutput WITHOUT question_to_user.

If valid:
{{
 "valid": true,
 "awaiting_user_input": false,
 "missing_fields": [],
 "sql": "<generated SQL>",
 "reason": null,
 "question": "{user_question}"
}}

If NOT valid:
{{
 "valid": false,
 "awaiting_user_input": false,
 "missing_fields": ["<short_reason_code>"],
 "sql": null,
 "reason": "<machine_reason_or_null>",
 "question": "{user_question}"
}}

------------------------------------------------------------
USER QUESTION:
------------------------------------------------------------
{user_question}
"""

        # MODEL CALL
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        content = (response.text or "").strip()

        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0].strip()

        debug("IntentAgent input (ctx.user_content)", getattr(state, "user_content", None))
        debug("User question extracted", user_question)
        debug("LLM raw response", response.text)

        # JSON PARSE fallback (non-JSON model output)
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {
                "valid": False,
                "reason": "model_non_json_response",
                "awaiting_user_input": False,
                "missing_fields": ["clarification_needed"],
                "sql": None,
                "question": user_question,
            }

        # -----------------------------
        # ✅ ADDITION: numeric filter fix
        # -----------------------------
        def _fix_numeric_filters(sql: str) -> str:
            if not sql:
                return sql

            # app_id = 2  -> app_id = "app_id_2"
            sql = re.sub(
                r'app_id\s*=\s*(\d+)',
                r'app_id = "app_id_\1"',
                sql
            )

            # media_source = 2 -> media_source = "media_source_2"
            sql = re.sub(
                r'media_source\s*=\s*(\d+)',
                r'media_source = "media_source_\1"',
                sql
            )

            # partner = 2 -> partner = "partner_2"
            sql = re.sub(
                r'partner\s*=\s*(\d+)',
                r'partner = "partner_\1"',
                sql
            )

            # site_id = 12 -> site_id = "site_id_12"
            sql = re.sub(
                r'site_id\s*=\s*(\d+)',
                r'site_id = "site_id_\1"',
                sql
            )

            return sql

        if parsed.get("valid") and parsed.get("sql"):
            parsed["sql"] = _fix_numeric_filters(parsed["sql"])

        # Validate against schema if possible
        try:
            clean_state = AgentAOutput(**parsed).model_dump()
        except Exception:
            clean_state = parsed

        logger.debug(f"[IntentAgent] Final clean_state = {clean_state}")

        return {
            "state": clean_state,
            "should_run_focus": not clean_state.get("valid", False),
            "should_run_executor": clean_state.get("valid", False),
            "should_run_explainer": False,
        }