from google.cloud import bigquery
from typing import List, Dict, Any, Optional

# Reuse existing chart utilities and output shape for consistency
from main_agent.sub_agents.d_explanation_agent.chart_generator import (
    rows_to_echarts_options,
    chart_options_to_png_base64,
)
from main_agent.sub_agents.d_explanation_agent.schemas import ExplanationOutput

PROJECT = "practicode-2025"
DATASET = "clicks_data_prac"
TABLE = f"{PROJECT}.{DATASET}.media_source_anomalies"

client = bigquery.Client(project=PROJECT)

class AnomalyAgent:

    def get_all_anomalies(self):
        sql = f"""
        SELECT *
        FROM `{TABLE}`
        ORDER BY ratio DESC
        LIMIT 200
        """
        return list(client.query(sql).result())

    def get_media_source_anomalies(self, media_source):
        sql = f"""
        SELECT *
        FROM `{TABLE}`
        WHERE media_source = '{media_source}'
        ORDER BY ratio DESC
        """
        return list(client.query(sql).result())

    def get_anomalies_by_hour(self, day, hour):
        sql = f"""
        SELECT *
        FROM `{TABLE}`
        WHERE day_date = '{day}'
          AND hour_of_day = {hour}
        ORDER BY ratio DESC
        """
        return list(client.query(sql).result())

    def answer(self, question: str):
        """
        Produce a chart response for anomalies without routing through the explainer.
        Returns an ExplanationOutput-compatible dict so the UI/root can render consistently.
        """
        q = (question or "").lower()

        # Show a ranked bar chart of the strongest anomalies across all sources
        if "כל" in q or "all" in q:
            rows = self.get_all_anomalies()
            return self._chart_top_anomalies(rows)

        # If the question contains a media source hint, try to extract it simply
        if "media" in q or "מקור" in q:
            parts = [p.strip(",.:") for p in q.split()]
            media_value = None
            # naive extraction: token after 'media' or token containing '=' style
            for i, p in enumerate(parts):
                if p == "media" and i + 1 < len(parts):
                    media_value = parts[i + 1]
                    break
                if p.startswith("media="):
                    media_value = p.split("=", 1)[1]
                    break
            if media_value:
                rows = self.get_media_source_anomalies(media_value)
                return self._chart_media_over_time(rows, media_value)
            # fallback: try as-is
            return self._chart_media_over_time(self.get_media_source_anomalies(q), q)

        if "שעה" in q or "hour" in q:
            # Could be extended to a specific hour/day chart, leaving as a friendly message for now
            return ExplanationOutput(
                status="success",
                description="Visualization by hour will be added soon — please specify media/day to focus.",
                render_type="text",
            ).model_dump()

        # Default: show overall top anomalies
        rows = self.get_all_anomalies()
        return self._chart_top_anomalies(rows)

    def format_results(self, rows):
        if not rows:
            return "לא נמצאו אנומליות."

        text = "🔥 אנומליות שנמצאו:\n\n"
        
        for r in rows:
            text += (
                f"• מקור {r['media_source']} ביום {r['day_date']} "
                f"שעה {r['hour_of_day']}: "
                f"Actual={r['actual_events']}, Expected={r['expected_events']}, "
                f"Ratio={r['ratio']:.2f}x\n"
            )

        return text

    # -----------------
    # Chart helpers
    # -----------------
    @staticmethod
    def _bq_rows_to_dicts(rows) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for r in rows:
            # BigQuery Row supports both attr and key access; normalize to dict
            try:
                out.append({k: r[k] for k in r.keys()})
            except Exception:
                out.append(dict(r))
        return out

    def _chart_media_over_time(self, rows, media_source: str) -> Dict[str, Any]:
        """Line chart: time on X, anomaly strength (|z|) on Y for a single media source."""
        data = self._bq_rows_to_dicts(rows)
        # sort by date/hour ascending for a sensible time series
        try:
            data.sort(key=lambda d: (str(d.get("day_date")), int(d.get("hour_of_day", 0))))
        except Exception:
            pass

        chart_rows = []
        for d in data:
            day = str(d.get("day_date"))
            hour = int(d.get("hour_of_day", 0))
            label = f"{day} {hour:02d}:00"
            ratio_val = d.get("ratio")
            try:
                ratio_float = float(ratio_val) if ratio_val is not None else 0.0
            except Exception:
                ratio_float = 0.0
            chart_rows.append({"time": label, "anomaly_strength": ratio_float})

        options = rows_to_echarts_options(
            chart_rows,
            chart_type="line",
            x_column="time",
            y_column="anomaly_strength",
            title=f"Anomaly strength over time — {media_source}",
        )
        img = chart_options_to_png_base64(options)
        out = ExplanationOutput(
            status="success",
            description=f"Detected anomalies for media source '{media_source}'.",
            render_type="chart",
            table_markdown=None,
            chart_image=img,
            chart_options=options,
        )
        return out.model_dump()

    def _chart_top_anomalies(self, rows) -> Dict[str, Any]:
        """Bar chart: top anomalies ranked by ratio across all sources."""
        data = self._bq_rows_to_dicts(rows)
        # take top 20 by ratio
        try:
            data.sort(key=lambda d: float(d.get("ratio", 0) or 0), reverse=True)
        except Exception:
            pass
        data = data[:20]

        chart_rows = []
        for d in data:
            try:
                label = f"{d.get('media_source')} {d.get('day_date')} {int(d.get('hour_of_day', 0)):02d}:00"
            except Exception:
                label = f"{d.get('media_source')} {d.get('day_date')} {d.get('hour_of_day')}"
            try:
                ratio_val = float(d.get("ratio", 0) or 0)
            except Exception:
                ratio_val = 0.0
            chart_rows.append({"anomaly": label, "ratio": ratio_val})

        options = rows_to_echarts_options(
            chart_rows,
            chart_type="bar",
            x_column="anomaly",
            y_column="ratio",
            title="Top anomalies by deviation ratio",
        )
        img = chart_options_to_png_base64(options)
        out = ExplanationOutput(
            status="success",
            description="Top anomalies detected across sources (ranked by ratio).",
            render_type="chart",
            table_markdown=None,
            chart_image=img,
            chart_options=options,
        )
        return out.model_dump()
