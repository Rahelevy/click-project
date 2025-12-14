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

        # Edge case: no question extracted
        if not user_question:
            clean = {
                "valid": False,
                "awaiting_user_input": True,
                "missing_fields": ["question"],
                "question_to_user": "לא קיבלתי שאלה. תוכלי לנסח שוב?",
                "sql": None,
                "reason": "missing_question",
                "question": "",
            }
            return {
                "state": clean,
                "should_run_focus": True,
                "should_run_executor": False,
                "should_run_explainer": False,
            }

        # Too broad / missing filters → send to Focus
        if self._looks_too_broad(user_question):
            is_hebrew = self._is_hebrew(user_question)
            question_to_user = (
                "השאלה מעט רחבה. אפשר למקד – למשל לפי אפליקציה, מקור תנועה, תאריך או סוג פעולה?"
                if is_hebrew else
                "This request is too broad. Could you narrow it down by app, source, date, or event type?"
            )

            clean = {
                "valid": False,
                "awaiting_user_input": True,
                "missing_fields": ["filter_needed"],
                "question_to_user": question_to_user,
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

        # ---- BUILD UPDATED PROMPT (ONLY CHANGE) ----
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

------------------------------------------------------------
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
  → Ask user to clarify

------------------------------------------------------------
DATE FORMAT RULE (MM-DD-YYYY)
------------------------------------------------------------
If the user writes a date like "10-24-2025", always interpret it as:
  MM-DD-YYYY → Month-Day-Year

So:
  "10-24-2025" → October 24, 2025

Compare this against the real current date.

------------------------------------------------------------
DATE FILTERING RULE (IMPORTANT — USE PARTITIONS!)
------------------------------------------------------------
The table practicode-2025.clicks_data_prac.encoded_clicks is
partitioned by DATE(event_time). Therefore:

- If the user provides a date or date range, you MUST filter using:
    DATE(event_time)

Correct usage examples:
  DATE(event_time) = "2025-10-24"
  DATE(event_time) BETWEEN "2025-10-24" AND "2025-10-26"

- If the user does NOT provide any date, do NOT invent one.
  (Date filtering is optional, but must be correct when given.)

NEVER compare raw timestamps unless the user explicitly asks for timestamp-level logic.

------------------------------------------------------------
SQL GENERATION RULES
------------------------------------------------------------
1. ALWAYS use:
   `practicode-2025.clicks_data_prac.encoded_clicks`

2. NEVER invent filters or values.

3. If NOT aggregating (raw rows):
   - You may SELECT the full row set (all fields listed below),
     but only when the user explicitly asks for rows / list / all clicks / raw data.

4. If the user provides a date range,
   ALWAYS use DATE(event_time) BETWEEN "<start-date>" AND "<end-date>".

------------------------------------------------------------
APP_ID FORMAT RULES
------------------------------------------------------------
The dataset uses synthetic app IDs in the form "app_id_<number>"
(e.g. "app_id_1", "app_id_2", "app_id_20").

1) If the user provides an app id as a plain number:
   YOU MUST convert it to:
   app_id = "app_id_<number>"

2) If the user provides an app id that is not numeric and does NOT start with "app_id_":
   - DO NOT generate a SQL query.
   - Ask the user to provide a valid app identifier in the "app_id_<number>" format.

------------------------------------------------------------
MEDIA SOURCE MAPPING RULES
------------------------------------------------------------
The dataset uses media sources in the format: media_source_<number>

1) If the user provides a number:
   YOU MUST convert it to:
       media_source = "media_source_<number>"

2) If the user provides a non-numeric media source that does not match media_source_<number>,
   you MUST ask for clarification and NOT generate SQL.

------------------------------------------------------------
PARTNER FIELD RULES
------------------------------------------------------------
The dataset uses partner identifiers in the strict format:
    partner_<number>

1) If the user provides a number referring to partner:
   YOU MUST convert it to:
       partner = "partner_<number>"

2) If the user provides a non-numeric partner not matching partner_<number>,
   you MUST ask for clarification and NOT generate SQL.

------------------------------------------------------------
SITE ID RULES
------------------------------------------------------------
The dataset uses site identifiers in the strict format:
    site_id_<number>

1) If the user provides a number referring to a site:
   YOU MUST convert it to:
       site_id = "site_id_<number>"

2) If the user does not provide a number for site_id when needed,
   the query is NOT valid. Ask for clarification.

------------------------------------------------------------
COUNT vs SUM RULES
------------------------------------------------------------
1) For "how many clicks / events / total clicks / כמה קליקים":
   MUST use:
       SUM(total_events)

2) For "how many rows / entries / כמה שורות":
   MUST use:
       COUNT(*)

------------------------------------------------------------
AGGREGATION DECISION (CRITICAL — NEW)
------------------------------------------------------------
When valid=true, you must decide whether the user wants RAW rows
or an AGGREGATED summary.

RAW triggers (no aggregation_spec):
- User explicitly asks for rows/list/raw data:
  "show me all clicks", "list events", "give me the rows",
  "תראי לי את כל הקליקים", "רשימה של קליקים", "נתונים גולמיים".

AGGREGATION triggers (include aggregation_spec):
- User asks for totals or summaries:
  "how many", "count clicks", "total events", "sum of clicks",
  "כמה", "סך הכל", "כמות קליקים".
- User asks for breakdown/grouping:
  "by partner", "by media source", "per app", "breakdown by X",
  "לפי שותף", "לפי מקור", "פילוח לפי X".
- User asks for top-N:
  "top 5 partners", "best sources", "top media sources".
- User asks for share/percent:
  "percentage", "share", "distribution", "אחוזים", "חלק מתוך הכל".
- User asks for trends over time:
  "trend", "daily/weekly/monthly clicks", "התפלגות לאורך זמן".

If AGGREGATION is needed:
1) Generate BASE SQL with filters only (NO GROUP BY, NO SUM).
2) Add "aggregation_spec" to the JSON output.

aggregation_spec format:
{{
  "group_by": ["<one or more columns>"] or [],
  "metric_alias": "clicks",
  "top_n": <optional int>,
  "add_percent": <optional true/false>,
  "time_granularity": <optional "hour"|"day"|"month">
}}

Rules:
- group_by columns must be from:
  event_time, hr, is_engaged_view, is_retargeting,
  media_source, partner, app_id, site_id
- If user asks only for TOTAL (no breakdown), set group_by=[].
- If user asks top N, set top_n=N.
- If user asks percent/share, set add_percent=true.
- If user asks time trend, group_by=["event_time"] and set time_granularity.

------------------------------------------------------------
WHEN TO ASK FOR CLARIFICATION
------------------------------------------------------------
CASE A – TOO BROAD  
Hebrew:
"השאלה מעט רחבה. אפשר לחדד או למקד – למשל לפי אפליקציה, מקור תנועה, תאריך או סוג פעולה?"
English:
"This request is a bit too broad. Could you narrow it down – for example by app, traffic source, date, or event type?"

CASE B – UNSUPPORTED FIELD  
Hebrew:
"נראה שהתייחסת למידע שאין לנו עליו נתונים. אפשר לציין אפליקציה, מקור תנועה או טווח תאריכים?"
English:
"It seems you mentioned information we do not have data for. Could you specify something like an app, a traffic source, or a date range?"

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
If the query is valid and enough information exists,
return JSON ONLY in this shape:

{{
 "valid": true,
 "awaiting_user_input": false,
 "missing_fields": [],
 "question_to_user": null,
 "sql": "<generated base SQL>",
 "aggregation_spec": <optional object or null>,
 "reason": null,
 "question": "{user_question}"
}}

If NOT valid, return:

{{
 "valid": false,
 "awaiting_user_input": true,
 "missing_fields": ["<short_reason_code>"],
 "question_to_user": "<friendly explanation in the same language>",
 "sql": null,
 "aggregation_spec": null,
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
            is_hebrew = self._is_hebrew(user_question)
            question_to_user = (
                "לא הצלחתי להבין את הבקשה. תוכלי לחדד?"
                if is_hebrew else
                "I could not understand your request. Could you clarify?"
            )

            parsed = {
                "valid": False,
                "reason": "model_non_json_response",
                "awaiting_user_input": True,
                "missing_fields": ["clarification_needed"],
                "question_to_user": question_to_user,
                "sql": None,
                "question": user_question,
            }

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
