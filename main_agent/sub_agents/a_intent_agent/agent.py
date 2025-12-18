import logging
logger = logging.getLogger("intent")
logger.debug("🔥 IntentAgent loaded")

from multiprocessing.util import debug
from google.adk.agents import BaseAgent
from google import genai
import json
import os
import re
from datetime import date  # ✅ ADDED (only for today's date anchor)
from datetime import datetime

from .schemas import AgentAOutput
from dotenv import load_dotenv

# Load .env from main_agent/.env explicitly (fallback to default search)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
try:
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
    else:
        load_dotenv()
except Exception:
    load_dotenv()


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
    def _normalize_dates_in_text(text: str) -> str:
        """
        Normalize common date tokens in the text to ISO yyyy-mm-dd.
        Supports:
        - dd-mm-yyyy, dd/mm/yyyy, dd.mm.yyyy (first part > 12 → treat as day)
        - mm-dd-yyyy (US) when first part <= 12
        """
        if not text:
            return text

        def _norm(m: re.Match) -> str:
            a = int(m.group(1))
            b = int(m.group(2))
            y = int(m.group(3))
            # decide format: if a > 12 assume dd-mm-yyyy, else mm-dd-yyyy
            if a > 12:
                day, month = a, b
            else:
                month, day = a, b
            try:
                dt = datetime(y, month, day)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                # if invalid date, keep original token
                return m.group(0)

        pattern = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b")
        return pattern.sub(_norm, text)

    @staticmethod
    def _extract_app_id(text: str) -> str | None:
        if not text:
            return None
        m = re.search(r"\bapp[_ ]?id[_ ]?(\d+)\b", text, flags=re.IGNORECASE)
        if m:
            return f"app_id_{m.group(1)}"
        m = re.search(r"\bapp_id_(\d+)\b", text, flags=re.IGNORECASE)
        if m:
            return f"app_id_{m.group(1)}"
        return None

    @staticmethod
    def _extract_single_iso_date(text: str) -> str | None:
        if not text:
            return None
        m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _add_limit_to_sql(sql: str, limit: int = 1000) -> str:
        """
        Appends a LIMIT clause to the SQL if not already present.
        """
        if not sql:
            return sql
        sql_lower = sql.lower()
        if "limit" in sql_lower:
            return sql
        # Add LIMIT before trailing semicolon if present
        sql = sql.rstrip()
        if sql.endswith(';'):
            sql = sql[:-1]
            return f"{sql} LIMIT {limit};"
        return f"{sql} LIMIT {limit}"

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
             "view"
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

    # =========================
    # NUMERIC FILTER FIXER (your addition)
    # =========================
    @staticmethod
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

    # ✅ NEW =========================
    # FORCE AGGREGATION WHEN USER ASKS "HOW MANY CLICKS"
    # ✅ NEW =========================
    @staticmethod
    def _wants_total_clicks(question: str) -> bool:
        if not question:
            return False

        q = question.lower()

        heb = [
            "כמה קליקים", "סך קליקים", "סה\"כ קליקים", "כמות קליקים", "סך הכל קליקים",
            "כמה אירועים", "סך אירועים", "סה\"כ אירועים"
        ]
        eng = [
            "how many clicks", "total clicks", "number of clicks",
            "how many events", "total events", "sum of clicks", "sum of events"
        ]

        return any(p in question for p in heb) or any(p in q for p in eng)

    # ✅ NEW
    @staticmethod
    def _rewrite_sql_to_sum_total_events(sql: str) -> str:
        """
        Turns:
          SELECT <anything> FROM `table` WHERE <filters>
        Into:
          SELECT SUM(total_events) AS total_clicks FROM `table` WHERE <filters>

        Keeps FROM/WHERE/... suffix as-is.
        """
        if not sql:
            return sql

        m = re.match(r"(?is)^\s*select\s+.*?\s+from\s+", sql)
        if not m:
            return sql

        return re.sub(
            r"(?is)^\s*select\s+.*?\s+from\s+",
            "SELECT SUM(total_events) AS total_clicks FROM ",
            sql,
            count=1
        )

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


        user_question = (user_question or "").strip()
        # Normalize dates to ISO to reduce ambiguity (e.g., 24-10-2025 → 2025-10-24)
        user_question = self._normalize_dates_in_text(user_question)

        # Deterministic minimal SQL: if at least one field (app_id and/or date) exists, build SQL without LLM.
        app_id_val = self._extract_app_id(user_question)
        date_val = self._extract_single_iso_date(user_question)
        if app_id_val or date_val:
            where_clauses = []
            if app_id_val:
                where_clauses.append(f"app_id = \"{app_id_val}\"")
            if date_val:
                where_clauses.append(f"DATE(event_time) = \"{date_val}\"")
            where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"
            base_sql = (
                "SELECT event_time, hr, media_source, partner, app_id, site_id, "
                "is_retargeting, is_engaged_view, total_events "
                "FROM `practicode-2025.clicks_data_prac.encoded_clicks` "
                f"WHERE {where_sql}"
            )
            base_sql = self._add_limit_to_sql(base_sql)

            clean_state = {
                "valid": True,
                "awaiting_user_input": False,
                "missing_fields": [],
                "question_to_user": None,
                "sql": base_sql,
                "aggregation_spec": None,
                "reason": None,
                "question": user_question,
            }
            logger.info(f"[IntentAgent] Deterministic SQL (no LLM) = {clean_state['sql']}")
            return {
                "state": clean_state,
                "should_run_focus": False,
                "should_run_executor": True,
                "should_run_explainer": False,
            }



        # ✅ NEW: normalize "app id 20" / "appid 20" / "app_id 20" into "app_id_20"
        m = re.search(r"\bapp(?:_?id)?\s*(\d+)\b", user_question, flags=re.IGNORECASE)
        if m:
            n = m.group(1)
            user_question = re.sub(
                r"\bapp(?:_?id)?\s*\d+\b",
                f"app_id_{n}",
                user_question,
                flags=re.IGNORECASE
            )
        elif re.fullmatch(r"\d+", user_question):
            user_question = f"app_id_{user_question}"

        # ✅ ADDED: real "today" anchor for date validation (no behavior change)
        today_str = date.today().isoformat()






        # Edge case: no question extracted (A handles it directly)

        if not user_question:
            clean = {
                "valid": False,
                "awaiting_user_input": True,
                "missing_fields": ["question"],
                "question_to_user": None,
                "sql": None,
                "reason": "missing_question",
                "question": "",
            }
            return {
                "state": clean,
                "should_run_focus": False,
                "should_run_executor": False,
                "should_run_explainer": False,
            }

        # Too broad / missing filters → send to Focus
        if self._looks_too_broad(user_question):
            clean = {
                "valid": False,
                "awaiting_user_input": False,
                "missing_fields": ["filter_needed"],
                "question_to_user": None,
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


        # ✅ ADDED: real "today" anchor for date validation (no behavior change)
        today_str = date.today().isoformat()  # e.g. "2025-12-10"

        # ---- BUILD YOUR FULL PROMPT (only addition is TODAY'S DATE block) ----

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
TODAY'S DATE (for validation)
------------------------------------------------------------
{today_str}

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

- If the user provides a date or date range, you MUST filter using:
    DATE(event_time)

Correct usage examples:
  DATE(event_time) = "2025-10-24"
  DATE(event_time) BETWEEN "2025-10-24" AND "2025-10-26"



NEVER compare raw timestamps unless the user explicitly asks for timestamp-level logic.

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

2. NEVER invent filters or values.

3. NEVER return all columns by default.
   Allowed:
   - SELECT SUM(total_events)
   - SELECT aggregated data


4. If NOT aggregating (raw rows):
   - You may SELECT the full row set (all fields listed below),
     but only when the user explicitly asks for rows / list / all clicks / raw data.


5. If the user provides a date range,
   ALWAYS use DATE(event_time) BETWEEN "<start-date>" AND "<end-date>".

6. NEVER invent filters or values.

APP_ID FORMAT RULES
------------------------------------------------------------
The dataset uses synthetic app IDs in the form "app_id_<number>"
(e.g. "app_id_1", "app_id_2", "app_id_20").

1) If the user provides an app id as a plain number:
   YOU MUST convert it to:
   app_id = "app_id_<number>"


2) If the user provides an app id that is not numeric and does NOT start with "app_id_",
   such as "test.app", "com.app.test", or any other package-like string:

   - DO NOT generate a SQL query.
   - Treat the question as invalid.
   - Return valid=false, awaiting_user_input=false,
     missing_fields including "app_id", and sql=null.

------------------------------------------------------------
AGGREGATION RULES — CRITICAL
------------------------------------------------------------
You must NOT use SUM(), COUNT(), or any aggregation function
unless the user explicitly asks for an aggregated metric.

(keep your original triggers...)


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
 "awaiting_user_input": false,
 "missing_fields": ["<short_reason_code>"],
 "question_to_user": null,
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

        # MODEL CALL (Gemini)
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
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

            # A לא שואל את המשתמש. רק מסמן שחסר מיקוד/הבהרה כדי ש-B ישאל.
            parsed = {
                "valid": False,
                "reason": "model_non_json_response",
                "awaiting_user_input": False,   # חשוב: לא לעצור את הזרימה פה
                "missing_fields": ["clarification_needed"],
                "question_to_user": None,
                "sql": None,
                "question": user_question,
            }

        # ✅ ADDED: fix numeric filters after JSON if valid
        if parsed.get("valid") and parsed.get("sql"):
            parsed["sql"] = self._fix_numeric_filters(parsed["sql"])

        # ✅ NEW: force SUM(total_events) when the user asks "how many clicks/events"
        if parsed.get("valid") and parsed.get("sql") and self._wants_total_clicks(user_question):
            parsed["sql"] = self._rewrite_sql_to_sum_total_events(parsed["sql"])

        # ✅ NEW: Add LIMIT to prevent buffer allocation errors in BigQuery
        if parsed.get("valid") and parsed.get("sql"):
            parsed["sql"] = self._add_limit_to_sql(parsed["sql"])

        # Validate against schema if possible
        try:
            clean_state = AgentAOutput(**parsed).model_dump()
        except Exception:
            clean_state = parsed

        logger.debug(f"[IntentAgent] Final clean_state = {clean_state}")
        
        is_valid = bool(clean_state.get("valid"))
        return {
            "state": clean_state,
            "should_run_focus": not clean_state.get("valid", False),
            "should_run_executor": is_valid,
            "should_run_explainer": False,
        }
