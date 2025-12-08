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
import os
load_dotenv()   # <-- FORCE LOAD .env


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

        # Extract user question (your original)
        try:
            user_question = state.user_content.parts[0].text
        except Exception:
            user_question = getattr(state, "question", None) or str(state)

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


        # ---- BUILD YOUR FULL PROMPT (unchanged) ----
        prompt = f"""
You are Agent A – the Intent Analyzer for a BigQuery dataset.

------------------------------------------------------------
LANGUAGE RULE (IMPORTANT)
------------------------------------------------------------
Respond in the same language the user used:
- If the question is in Hebrew → respond in Hebrew.
- If the question is in English → respond in English.
Never switch the user's language.





Always add:
  LIMIT 500
at the end of every SQL query unless the user explicitly asks for ALL rows.
This prevents heavy full-table scans that could freeze the system.




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
  → Ask user to clarify
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

If the user specifies a single date like "10-24-2025",
interpret it as MM-DD-YYYY → October 24, 2025, and generate:

  DATE(event_time) = "2025-10-24"

If the user specifies a date range:
  - Normalize and reorder them if needed.
  - Always use:

      DATE(event_time) BETWEEN "<start-date>" AND "<end-date>"

NEVER generate:
  event_time >= "<date> 00:00:00 UTC"
  event_time < "<next day> 00:00:00 UTC"

because this bypasses the date partition, causes a full table scan,
and severely slows down BigQuery. Always use DATE(event_time) filters.

------------------------------------------------------------
SQL GENERATION RULES
------------------------------------------------------------
1. ALWAYS use:
   `practicode-2025.clicks_data_prac.encoded_clicks`

2. NEVER return all columns by default.
   Allowed:
   - SELECT SUM(total_events)
   - SELECT aggregated data

3. DO NOT generate SELECT event_time, hr, ...
   unless user explicitly requests “all fields” or a non-aggregated list.

4. Date ranges MUST follow:
   event_time >= '<start> 00:00:00 UTC'
   AND event_time < '<end + 1 day> 00:00:00 UTC'

5. NEVER invent filters or values.

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

   Example:
   "app id = 2" → app_id = "app_id_2"
   "app id 5"   → app_id = "app_id_5"

2) If the user provides an app id that is not numeric and does NOT start with "app_id_",
   such as "test.app", "com.app.test", or any other package-like string:

   - DO NOT generate a SQL query.
   - Treat the question as invalid.
   - Ask the user to provide a valid app identifier in the "app_id_<number>" format.

   The JSON you return in that case MUST have:
   - valid = false
   - awaiting_user_input = true
   - sql = null
   - question_to_user = a friendly clarification message in the user's language

------------------------------------------------------------
AGGREGATION RULES — CRITICAL
------------------------------------------------------------
You must NOT use SUM(), COUNT(), or any aggregation function
unless the user explicitly asks for an aggregated metric.

Valid aggregation triggers include:

English:
- "how many"
- "how much"
- "count"
- "total clicks"
- "sum of events"
- "number of clicks"
- "show me the total"

Hebrew:
- "כמה"
- "כמה קליקים"
- "כמה אירועים"
- "כמה היה"
- "סך הכל"
- "כמות"
- "כמה התקבל"

If the user does NOT request aggregation:
→ The SQL MUST return individual rows, NOT a single summary value.

When NOT aggregating, your SELECT clause must explicitly include:
event_time, hr, is_engaged_view, is_retargeting,
media_source, partner, app_id, site_id,
engagement_type, total_events

For example:
SELECT
  event_time, hr, is_engaged_view, is_retargeting,
  media_source, partner, app_id, site_id,
  engagement_type, total_events

------------------------------------------------------------
MEDIA SOURCE MAPPING RULES
------------------------------------------------------------
The dataset uses media sources in the format: media_source_<number>

Examples:
- media_source_1
- media_source_257
- media_source_89

1) If the user provides a number (e.g. "media source 257", "source 10"),
   you MUST convert it to:
       media_source = "media_source_<number>"

2) If the user describes the media source in natural language, such as:
   English:
     - "the source that showed the ad"
     - "the ad provider"
     - "the advertiser source"
     - "where the ad was published"
   Hebrew:
     - "מקור הפרסום"
     - "מקום פרסום ההודעה"
     - "מאיפה המודעה הגיעה"
     - "מי הציג את המודעה"

   You MUST treat this as referring to the media_source field.

3) If the user provides a non-numeric media source that does not match
   the required format (media_source_<number>),
   you MUST ask the user for clarification and NOT generate SQL.

4) If the user explicitly writes "media_source_###",
   use it exactly as provided.

------------------------------------------------------------
PARTNER FIELD RULES
------------------------------------------------------------
The dataset uses partner identifiers in the strict format:
    partner_<number>

Examples:
- partner_1
- partner_22
- partner_136
- partner_502

1) If the user provides a number referring to the partner, such as:
   - "partner 136"
   - "partner = 5"
   - "the partner 22"
   - "שותף 10"

   You MUST convert it to the correct SQL value:
       partner = "partner_<number>"

2) If the user describes the partner in natural language (English or Hebrew),
   you MUST understand it refers to the partner field.

3) If the user provides a non-numeric partner (e.g. "partner google")
   which does NOT match the required format partner_<number>,
   you MUST NOT generate SQL.
   Instead, request clarification from the user.

4) If the user explicitly writes "partner_###", use it as is.

------------------------------------------------------------
SITE ID RULES
------------------------------------------------------------
The dataset uses site identifiers in the strict format:
    site_id_<number>

Examples:
- site_id_38238605550
- site_id_120
- site_id_887744112233

1) If the user provides a number referring to a site, such as:
   - "site 38238605550"
   - "site_id 12"
   - "the site 554433"
   - "publisher 111222333"

   You MUST convert it to:
       site_id = "site_id_<number>"

2) If the user describes the publisher/site in natural language (English or Hebrew),
   you MUST understand this refers to the site_id field.

3) If the user does not provide a number (e.g., "show me clicks by publisher"),
   the query is NOT valid.
   You must ask the user to provide a specific numeric site identifier.

4) If the user provides a non-numeric value such as:
   "site google", "publisher apple"
   you must NOT generate SQL and instead request clarification.

5) If the user explicitly writes "site_id_<number>",
   use it exactly as written.

------------------------------------------------------------
COUNT vs SUM RULES
------------------------------------------------------------
The dataset contains a field called total_events which represents
the number of raw events aggregated into each row.

Therefore:

1) If the user asks “how many clicks”, “how many events”, “total clicks”,
   “sum of events”, “כמה קליקים”, etc. → 
   You MUST use:
       SUM(total_events)

2) If the user asks “how many rows”, “how many entries”, “כמה שורות”, etc. → 
   You MUST use:
       COUNT(*)

3) Never use COUNT(*) to answer questions asking about the number of
   clicks or events, because that would count rows instead of events.

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
you MUST return JSON ONLY in this shape:

{{
 "valid": true,
 "awaiting_user_input": false,
 "missing_fields": [],
 "question_to_user": null,
 "sql": "<generated SQL>",
 "reason": null,
 "question": "{user_question}"
}}

If the query is NOT valid, you MUST return:

{{
 "valid": false,
 "awaiting_user_input": true,
 "missing_fields": ["<short_reason_code>"],
 "question_to_user": "<friendly explanation in the same language>",
 "sql": null,
 "reason": "<machine_reason_or_null>",
 "question": "{user_question}"
}}

------------------------------------------------------------
USER QUESTION:
------------------------------------------------------------
{user_question}
"""

        # MODEL CALL (your original)
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

        # JSON PARSE (your original)
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
