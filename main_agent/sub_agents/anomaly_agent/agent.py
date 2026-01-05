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
        """Time-series line charts showing actual clicks over time for top anomalies."""
        data = self._bq_rows_to_dicts(rows)
        # take top anomalies by ratio
        try:
            data.sort(key=lambda d: float(d.get("ratio", 0) or 0), reverse=True)
        except Exception:
            pass
        
        # Get top 5 anomalies and create time-series charts for each
        top_anomalies = data[:5]
        
        if not top_anomalies:
            return ExplanationOutput(
                status="success",
                description="No anomalies detected.",
                render_type="text",
            ).model_dump()
        
        # For the strongest anomaly, create a detailed time-series chart
        strongest = top_anomalies[0]
        media_source = strongest.get("media_source")
        anomaly_day = str(strongest.get("day_date"))
        anomaly_hour = int(strongest.get("hour_of_day", 0))
        absolute_gap = strongest.get("absolute_gap", 0)
        
        # Fetch time series around the anomaly (past and future) for comparison
        # This allows users to see the normal baseline hours before the spike
        sql = f"""
        SELECT
          day_date,
          hour_of_day,
          total_clicks
        FROM `{PROJECT}.{DATASET}.media_source_hourly_agg`
        WHERE media_source = '{media_source}'
        ORDER BY day_date, hour_of_day
        """
        
        try:
            time_series_rows = list(client.query(sql).result())
            ts_data = self._bq_rows_to_dicts(time_series_rows)
            
            # Filter to show a window around the anomaly (a few hours before and after)
            # Calculate the anomaly timestamp for comparison
            from datetime import datetime, timedelta
            try:
                anomaly_dt = datetime.strptime(anomaly_day, "%Y-%m-%d")
                anomaly_timestamp = anomaly_dt.replace(hour=anomaly_hour)
                
                # Show data from 4 hours before to 4 hours after the anomaly
                start_time = anomaly_timestamp - timedelta(hours=4)
                end_time = anomaly_timestamp + timedelta(hours=4)
                
                # Filter data to this window
                filtered_data = []
                for d in ts_data:
                    day_str = str(d.get("day_date"))
                    hour = int(d.get("hour_of_day", 0))
                    try:
                        dt = datetime.strptime(day_str, "%Y-%m-%d").replace(hour=hour)
                        if start_time <= dt <= end_time:
                            filtered_data.append(d)
                    except:
                        pass
                
                ts_data = filtered_data if filtered_data else ts_data
            except:
                pass  # If filtering fails, use all data
            
            # Create chart data with proper timestamps
            chart_rows = []
            for d in ts_data:
                day_str = str(d.get("day_date"))
                hour = int(d.get("hour_of_day", 0))
                clicks = d.get("total_clicks", 0)
                # Create cleaner timestamp string (just date and hour)
                # Format: "10-24 15:00" instead of "2025-10-24 15:00"
                try:
                    # Extract month-day only
                    date_parts = day_str.split("-")
                    if len(date_parts) == 3:
                        timestamp = f"{date_parts[1]}-{date_parts[2]} {hour:02d}:00"
                    else:
                        timestamp = f"{day_str} {hour:02d}:00"
                except:
                    timestamp = f"{day_str} {hour:02d}:00"
                
                chart_rows.append({
                    "time": timestamp,
                    "clicks": float(clicks) if clicks is not None else 0.0
                })
            
            options = {
                "title": {"text": f"Media Source: {media_source} (Anomaly on {anomaly_day} at hour {anomaly_hour}, Gap: {absolute_gap})"},
                "tooltip": {"trigger": "axis"},
                "grid": {"left": "10%", "right": "10%", "bottom": "15%", "containLabel": True},
                "xAxis": {
                    "type": "category",
                    "data": [row["time"] for row in chart_rows]
                },
                "yAxis": {"type": "value"},
                "series": [
                    {
                        "type": "line",
                        "data": [row["clicks"] for row in chart_rows],
                        "smooth": True,
                        "name": "Clicks per Hour"
                    }
                ]
            }
            img = chart_options_to_png_base64(options)
            
            # Create a clear, user-friendly description
            description = f"""
📊 **Strongest Anomaly**

🔴 Media Source: {media_source}
📅 {anomaly_day} at {anomaly_hour:02d}:00
📈 {absolute_gap:,.0f} extra clicks ({strongest.get('ratio', 0):.2f}x above normal)
"""
            
            # Add summary of other top anomalies (compact version)
            if len(top_anomalies) > 1:
                description += "\n**Other anomalies:** "
                other_list = []
                for anom in top_anomalies[1:4]:
                    media = anom.get('media_source')
                    hour = anom.get('hour_of_day')
                    ratio = anom.get('ratio', 0)
                    other_list.append(f"{media} {hour}:00 ({ratio:.2f}x)")
                description += " • ".join(other_list)
            
            out = ExplanationOutput(
                status="success",
                description=description.strip(),
                render_type="chart",
                table_markdown=None,
                chart_image=img,
                chart_options=options,
            )
            return out.model_dump()
            
        except Exception as e:
            # Fallback to simple text if query fails
            return ExplanationOutput(
                status="success",
                description=f"Top anomaly: {media_source} on {anomaly_day} at {anomaly_hour}:00 (Error loading chart: {e})",
                render_type="text",
            ).model_dump()
