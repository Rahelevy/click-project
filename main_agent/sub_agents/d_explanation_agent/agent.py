from google.adk.agents import BaseAgent
from google import genai
import json
import os
import re
from dotenv import load_dotenv

from .schemas import ExplanationInput, ExplanationOutput
from .chart_generator import rows_to_echarts_options, auto_chart_type, chart_options_to_png_base64


def _normalize_chart_options(value):
    """Ensure chart options are a Python dict; accept JSON strings."""
    if not value:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
            return loaded if isinstance(loaded, dict) else None
        except Exception:
            return None
    return None


def _detect_top_request(question: str) -> bool:
    """Heuristic to see if the user asked for the top/most item."""
    if not question:
        return False
    q_lower = question.lower()
    keywords = ["most", "highest", "top", "max", "largest", "leading", "biggest", "maximum"]
    hebrew_keywords = ["הכי הרבה", "הגבוה", "מוביל", "מובילה", "גדול", "גבוהה"]
    return any(k in q_lower for k in keywords) or any(k in question for k in hebrew_keywords)


def _detect_chart_request(question: str) -> bool:
    """Heuristic to see if the user asked for a chart/graph/visualization."""
    if not question:
        return False
    q_lower = question.lower()
    keywords = ["chart", "graph", "plot", "visualize", "visualization", "show me a chart", "show me a graph"]
    hebrew_keywords = ["גרף", "תרשים", "ויזואליזציה", "הצג", "הראה"]
    return any(k in q_lower for k in keywords) or any(k in question for k in hebrew_keywords)


def _compute_top_finding(question, rows):
    """Compute the top row by metric when the question asks for "most"/"top"."""
    if not rows or not isinstance(rows, list):
        return None
    if not _detect_top_request(question):
        return None

    def is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    sample_row = rows[0] if isinstance(rows[0], dict) else None
    if not sample_row:
        return None

    metric_candidates = ["clicks", "count", "total", "value", "metric", "click_count"]
    dimension_candidates = ["media_source", "source", "channel", "campaign", "name", "partner"]

    metric_key = None
    for key in metric_candidates:
        if key in sample_row and is_number(sample_row[key]):
            metric_key = key
            break
    if not metric_key:
        for key, value in sample_row.items():
            if is_number(value):
                metric_key = key
                break
    if not metric_key:
        return None

    dimension_key = None
    for key in dimension_candidates:
        if key in sample_row:
            dimension_key = key
            break
    if not dimension_key:
        for key, value in sample_row.items():
            if not is_number(value):
                dimension_key = key
                break
    if not dimension_key:
        return None

    top_row = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        if metric_key not in row or dimension_key not in row:
            continue
        if not is_number(row[metric_key]):
            continue
        if top_row is None or row[metric_key] > top_row[metric_key]:
            top_row = row

    if not top_row:
        return None

    return {
        "dimension_key": dimension_key,
        "dimension_value": top_row.get(dimension_key),
        "metric_key": metric_key,
        "metric_value": top_row.get(metric_key),
    }


# ✅ NEW SYSTEM PROMPT:
# - DO NOT output markdown tables at all.
# - If db_result exists, render_type must be "table" and table_markdown must be null.
# - description must be short title only.
EXPLANATION_SYSTEM_PROMPT = """
You are AGENT D — the final layer before answering the end user.

INPUT YOU RECEIVE:
- user_question: user's natural-language question.
- incoming: JSON object from EXECUTOR:
    {
        "status": "success" or "error",
        "description": "<technical info>"
    }
- db_result: optional list of rows (list[dict]) returned from the database.

YOUR JOB:
Return a short user-friendly explanation AND structured UI payload.

ABSOLUTE RULES:
1. Respond in the same language as user_question (Hebrew or English).
2. Always return JSON ONLY in this exact format:
{
  "status": "success" | "error",
  "description": "<short title / caption ONLY>",
  "render_type": "text" | "table" | "chart",
  "table_markdown": null,
  "chart_options": null
}

CRITICAL UI RULE (IN ORDER OF PRIORITY):
1. If user explicitly asked for a chart / graph / visualization / plot:
   - You MUST return render_type="chart" (even if db_result exists)
   - Set chart_options to null (will be auto-generated from db_result)
   - description should be a short caption matching the chart request.

2. Else, if db_result exists and has at least 1 row:
   - You MUST return render_type="table"
   - description MUST be a short title that matches the content.
   - table_markdown MUST ALWAYS be null (NEVER output markdown tables).
   - NEVER mention row limits ("first 20", "only 20", etc.)
   - NEVER dump the table in text.
   - The frontend will render the table using db_result.

3. If no db_result and no chart needed:
   - Return render_type="text" and a short friendly answer.

Never output SQL.
Never invent data.
Return JSON ONLY.
"""


def _extract_app_id_from_question(q: str):
    if not q:
        return None
    m = re.search(r"\bapp[\s_]?id\b[:\s]*([0-9]+)\b", q.lower())
    if m:
        return m.group(1)
    # also catch "app_id_20"
    m = re.search(r"app_id[_\s]?([0-9]+)", q.lower())
    if m:
        return m.group(1)
    return None


class ExplainerAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="explainer_agent")

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

        object.__setattr__(self, "client", genai.Client(api_key=api_key))

    def run(self, state):
        # Handle both Pydantic model and dict inputs
        if isinstance(state, dict):
            user_question = state.get("user_question", "")
            incoming = state.get("incoming", {})
            db_result = state.get("db_result")
            if isinstance(incoming, dict):
                incoming_json = json.dumps(incoming, ensure_ascii=False)
            else:
                incoming_json = incoming.model_dump_json()
        else:
            user_question = state.user_question
            incoming_json = state.incoming.model_dump_json()
            db_result = getattr(state, "db_result", None)

        # ✅ PIPELINE GUARD (THE IMPORTANT PART):
        # If db_result exists, do NOT let the model build a markdown table.
        # We still ask it to generate only a short title.
        has_rows = isinstance(db_result, list) and len(db_result) > 0

        # If the user asked for "most/top", pre-compute the leader to guide the LLM
        top_hint = ""
        top_finding = _compute_top_finding(user_question, db_result)
        if top_finding:
            top_hint = f"""
--------------------
PRE-COMPUTED SUMMARY:
--------------------
Top {top_finding['metric_key']} by {top_finding['dimension_key']}: {top_finding['dimension_value']} with {top_finding['metric_value']} {top_finding['metric_key']}. Use this as the primary answer for any 'most/highest/top' question.
"""

        # Build prompt
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

{top_hint}

--------------------
DB RESULT STATS:
--------------------
Rows: {len(db_result) if has_rows else 0}
Example row keys: {list(db_result[0].keys()) if has_rows and isinstance(db_result[0], dict) else []}
"""

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )

        content = (response.text or "").strip()

        # Strip code fences if any
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0].strip()

        try:
            parsed = json.loads(content)
        except Exception:
            raise ValueError(f"Agent D returned invalid JSON:\n{content}")

        default_status = (
            state.incoming.status if hasattr(state, "incoming")
            else state.get("incoming", {}).get("status", "unknown")
        )

        # ✅ Check if user asked for a chart
        user_wants_chart = _detect_chart_request(user_question)

        # ✅ FORCE CLEAN OUTPUT IN TABLE CASE (unless user wants chart):
        if has_rows and not user_wants_chart:
            app_id = _extract_app_id_from_question(user_question)
            # If model didn't give good title, create one
            if not parsed.get("description"):
                if app_id:
                    parsed["description"] = f"Click summary for app ID {app_id}"
                else:
                    parsed["description"] = "Click summary"

            parsed["render_type"] = "table"
            parsed["table_markdown"] = None
            parsed["chart_options"] = None

            # Ensure no "first 20" appears
            parsed["description"] = re.sub(r"first\s+\d+\s+rows.*", "", parsed["description"], flags=re.IGNORECASE).strip()
        
        # ✅ If user wants chart and has data, force chart mode
        elif has_rows and user_wants_chart:
            if parsed.get("render_type") != "chart":
                parsed["render_type"] = "chart"
            parsed["table_markdown"] = None

        # Normalize chart options if chart
        chart_options = _normalize_chart_options(parsed.get("chart_options"))
        chart_image_markdown = None

        if parsed.get("render_type") == "chart" and not chart_options and db_result:
            try:
                chart_type = auto_chart_type(user_question, db_result)
                chart_options = rows_to_echarts_options(
                    db_result,
                    chart_type=chart_type,
                    title=parsed.get("description", "Chart"),
                    user_question=user_question  # ✅ Pass user question for smart column detection
                )
            except Exception as e:
                print(f"Warning: Failed to generate chart: {e}")

        if parsed.get("render_type") == "chart" and chart_options:
            try:
                chart_image_markdown = chart_options_to_png_base64(chart_options)
            except Exception as e:
                print(f"Warning: Failed to render PNG: {e}")

        output = ExplanationOutput(
            status=parsed.get("status", default_status),
            description=parsed.get("description", ""),
            render_type=parsed.get("render_type"),
            table_markdown=None,  # ✅ always null now
            chart_image=chart_image_markdown,
            chart_options=chart_options,
        )

        return {
            "state": output,
            "should_run_focus": False,
            "should_run_executor": False,
            "should_run_explainer": False,
        }
