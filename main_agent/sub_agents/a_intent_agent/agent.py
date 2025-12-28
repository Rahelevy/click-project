import logging
import json
import os
import re
from datetime import datetime

from google.adk.agents import BaseAgent
from google import genai
from dotenv import load_dotenv

from .schemas import AgentAOutput

logger = logging.getLogger("intent")
logger.debug("🔥 IntentAgent loaded")

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
        if api_key:
            object.__setattr__(self, "client", genai.Client(api_key=api_key))
        else:
            object.__setattr__(
                self,
                "client",
                genai.Client(
                    vertexai=True,
                    project="practicode-2025",
                    location="us-central1",
                ),
            )

    # =========================
    # HELPERS
    # =========================
    @staticmethod
    def _is_hebrew(text: str) -> bool:
        return any("א" <= ch <= "ת" for ch in (text or ""))

    @staticmethod
    def _normalize_dates_in_text(text: str) -> str:
        if not text:
            return text

        def _norm(m: re.Match) -> str:
            a = int(m.group(1))
            b = int(m.group(2))
            y = int(m.group(3))
            if a > 12:
                day, month = a, b
            else:
                month, day = a, b
            try:
                dt = datetime(y, month, day)
                return dt.strftime("%Y-%m-%d")
            except Exception:
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
    def _extract_media_source(text: str) -> str | None:
        if not text:
            return None
        m = re.search(r"\bmedia[_ ]?source[_ ]?(\d+)\b", text, flags=re.IGNORECASE)
        if m:
            return f"media_source_{m.group(1)}"
        m = re.search(r"\bmedia_source_(\d+)\b", text, flags=re.IGNORECASE)
        if m:
            return f"media_source_{m.group(1)}"
        return None

    @staticmethod
    def _extract_partner(text: str) -> str | None:
        if not text:
            return None
        m = re.search(r"\bpartner[_ ]?(\d+)\b", text, flags=re.IGNORECASE)
        if m:
            return f"partner_{m.group(1)}"
        m = re.search(r"\bpartner_(\d+)\b", text, flags=re.IGNORECASE)
        if m:
            return f"partner_{m.group(1)}"
        return None

    @staticmethod
    def _extract_site_id(text: str) -> str | None:
        if not text:
            return None
        m = re.search(r"\bsite[_ ]?id[_ ]?(\d+)\b", text, flags=re.IGNORECASE)
        if m:
            return f"site_id_{m.group(1)}"
        m = re.search(r"\bsite_id_(\d+)\b", text, flags=re.IGNORECASE)
        if m:
            return f"site_id_{m.group(1)}"
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
        if not sql:
            return sql
        if "limit" in sql.lower():
            return sql
        sql = sql.rstrip()
        if sql.endswith(";"):
            sql = sql[:-1]
            return f"{sql} LIMIT {limit};"
        return f"{sql} LIMIT {limit}"

    @staticmethod
    def _fix_numeric_filters(sql: str) -> str:
        """Convert numeric filters to encoded string ids, if needed."""
        if not sql:
            return sql

        sql = re.sub(r"app_id\s*=\s*(\d+)", r'app_id = "app_id_\1"', sql)
        sql = re.sub(r"media_source\s*=\s*(\d+)", r'media_source = "media_source_\1"', sql)
        sql = re.sub(r"partner\s*=\s*(\d+)", r'partner = "partner_\1"', sql)
        sql = re.sub(r'site_id\s*=\s*["\']?_?(\d+)["\']?', r'site_id = "site_id_\1"', sql)

        return sql

    # ✅ NEW =========================
    # ANOMALY DETECTION FAST PATH
    # =========================
    @staticmethod
    def _is_anomaly_query(question: str) -> bool:
        """Detect if user is asking about anomalies/outliers/unusual patterns."""
        if not question:
            return False

        q = question.lower()

        eng_keywords = [
            "anomaly", "anomalies", "outlier", "outliers",
            "unusual", "weird", "strange", "abnormal",
            "spike", "drop", "deviation", "unexpected",
            "suspicious", "suspiciously",
            "doesn't look normal", "don't look normal",
            "doesn't look right", "don't look right",
            "looks off", "look off",
            "out of the ordinary",
            "behave differently", "behaving differently",
            "doesn't match", "don't match",
            "something wrong", "what's wrong",
            "irregular", "irregularities",
        ]

        heb_keywords = [
            "אנומליה", "אנומליות", "חריג", "חריגים",
            "יוצא דופן", "מוזר", "לא רגיל", "בלתי צפוי",
            "קפיצה", "ירידה חדה", "סטייה", "חשוד", "לא נראה תקין",
        ]

        return any(kw in q for kw in eng_keywords) or any(kw in question for kw in heb_keywords)

    # ✅ NEW =========================
    # TOTAL CLICKS / EVENTS DETECTION
    # =========================
    @staticmethod
    def _wants_total_clicks(question: str) -> bool:
        if not question:
            return False

        q = question.lower()

        heb = [
            "כמה קליקים", "סך קליקים", 'סה"כ קליקים', "כמות קליקים", "סך הכל קליקים",
            "כמה אירועים", "סך אירועים", 'סה"כ אירועים',
        ]
        eng = [
            "how many clicks", "total clicks", "number of clicks",
            "how many events", "total events", "sum of clicks", "sum of events",
            "count of clicks", "count of the clicks", "count clicks", "count the clicks",
            "count of events", "count events",
        ]

        return any(p in question for p in heb) or any(p in q for p in eng)

    @staticmethod
    def _rewrite_sql_to_sum_total_events(sql: str) -> str:
        """
        Turns:
          SELECT <anything> FROM `table` WHERE <filters>
        Into:
          SELECT SUM(total_events) AS total_clicks FROM `table` WHERE <filters>
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
            count=1,
        )

    # =========================
    # MAIN RUN
    # =========================
    def run(self, state):
        logger.debug(f"[IntentAgent] Running with state= {state}")

        try:
            user_question = state.user_content.parts[0].text
        except Exception:
            if isinstance(state, dict):
                user_question = state.get("question")
            else:
                user_question = getattr(state, "question", None) or str(state)

        user_question = (user_question or "").strip()
        user_question = self._normalize_dates_in_text(user_question)

        # ✅ FAST PATH: anomaly queries
        if self._is_anomaly_query(user_question):
            logger.info("[IntentAgent] Detected anomaly query via keyword match")
            return {
                "state": AgentAOutput(
                    valid=True,
                    question=user_question,
                    query_type="anomaly",
                    sql=None,
                    awaiting_user_input=False,
                ).model_dump(),
                "should_run_focus": False,
                "should_run_executor": False,
                "should_run_explainer": False,
            }

        # ✅ extract all supported filters
        app_id_val = self._extract_app_id(user_question)
        date_val = self._extract_single_iso_date(user_question)
        media_source_val = self._extract_media_source(user_question)
        partner_val = self._extract_partner(user_question)
        site_id_val = self._extract_site_id(user_question)

        # ✅ deterministic SQL only when at least one filter exists
        if app_id_val or date_val or media_source_val or partner_val or site_id_val:
            where_clauses = []
            if app_id_val:
                where_clauses.append(f'app_id = "{app_id_val}"')
            if media_source_val:
                where_clauses.append(f'media_source = "{media_source_val}"')
            if partner_val:
                where_clauses.append(f'partner = "{partner_val}"')
            if site_id_val:
                where_clauses.append(f'site_id = "{site_id_val}"')
            if date_val:
                where_clauses.append(f'DATE(event_time) = "{date_val}"')

            where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

            # ✅ if the user asked for totals - aggregate
            if self._wants_total_clicks(user_question):
                base_sql = (
                    "SELECT SUM(total_events) AS total_clicks "
                    "FROM `practicode-2025.clicks_data_prac.encoded_clicks` "
                    f"WHERE {where_sql}"
                )
            else:
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
                "query_type": "sql",
                "aggregation_spec": None,
                "reason": None,
                "question": user_question,
            }

            logger.info(f"[IntentAgent] Deterministic SQL (fixed) = {clean_state['sql']}")
            return {
                "state": clean_state,
                "should_run_focus": False,
                "should_run_executor": True,
                "should_run_explainer": False,
            }

        # fallback
        return {
            "state": {
                "valid": False,
                "awaiting_user_input": False,
                "missing_fields": ["filter_needed"],
                "question_to_user": None,
                "sql": None,
                "reason": "too_broad",
                "question": user_question,
            },
            "should_run_focus": True,
            "should_run_executor": False,
            "should_run_explainer": False,
        }
