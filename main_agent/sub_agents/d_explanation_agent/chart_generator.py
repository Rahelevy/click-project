"""Generate charts using pyecharts from tabular data."""
import json
import base64
import io
from typing import List, Dict, Any, Optional

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from pyecharts.charts import Bar, Line, Pie
    from pyecharts import options as opts
    HAS_PYECHARTS = True
except ImportError:
    HAS_PYECHARTS = False


def chart_options_to_png_base64(options: Dict[str, Any]) -> Optional[str]:
    """
    Convert ECharts options dict to a base64-encoded PNG image.
    Returns markdown-safe data URI or None if matplotlib unavailable.
    """
    if not HAS_MATPLOTLIB or not options:
        return None
    
    try:
        # Extract data from ECharts options
        x_data = options.get("xAxis", {}).get("data", [])
        y_data = None
        chart_type = "bar"
        title = options.get("title", {}).get("text", "Chart")
        
        # Get first series
        series = options.get("series", [])
        if series:
            y_data = series[0].get("data", [])
            chart_type = series[0].get("type", "bar")
        
        if not x_data or not y_data:
            return None
        
        # Create figure with better size for time-series
        fig, ax = plt.subplots(figsize=(14, 6))
        
        if chart_type == "pie":
            # Pie chart
            ax.pie(y_data, labels=x_data, autopct='%1.1f%%', startangle=90)
        elif chart_type == "line":
            # Line chart
            ax.plot(x_data, y_data, marker='o', linewidth=2, markersize=4, label='Clicks per Hour')
            ax.set_ylabel("Clicks", fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.legend(loc='upper right', fontsize=10)
            
            # Better X-axis formatting for time-series
            # Sample every Nth label to avoid overlap
            n_labels = len(x_data)
            if n_labels > 20:
                step = max(1, n_labels // 15)  # Show ~15 labels max
                ax.set_xticks(range(0, n_labels, step))
                ax.set_xticklabels([x_data[i] for i in range(0, n_labels, step)], rotation=45, ha='right')
            else:
                ax.tick_params(axis='x', rotation=45)
                plt.setp(ax.xaxis.get_majorticklabels(), ha='right')
        else:
            # Bar chart (default)
            ax.bar(x_data, y_data, color='#5470c6', edgecolor='black', alpha=0.8)
            ax.set_ylabel("Clicks")
            ax.tick_params(axis='x', rotation=45)
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel("Category")
        
        # Tight layout to prevent label cutoff
        plt.tight_layout()
        
        # Encode as base64
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        
        # Return just the data URI, not wrapped in markdown
        return f"data:image/png;base64,{img_base64}"
    
    except Exception as e:
        print(f"Error converting chart to PNG: {e}")
        return None


def rows_to_echarts_options(
    rows: List[Dict[str, Any]],
    chart_type: str = "bar",
    x_column: Optional[str] = None,
    y_column: Optional[str] = None,
    title: str = "Chart",
    user_question: Optional[str] = None
) -> Dict[str, Any]:
    """Convert tabular data to a plain ECharts options dict (no HTML/JS).
    
    Args:
        rows: List of dictionaries with data
        chart_type: "bar", "line", or "pie"
        x_column: Column name for X-axis (auto-detect if None)
        y_column: Column name for Y-axis (auto-detect if None)
        title: Chart title
        user_question: Optional user question for smart column detection
    """
    if not rows:
        return {}

    # Auto-detect columns intelligently based on user question
    if x_column is None or y_column is None:
        columns = list(rows[0].keys())
        question_lower = (user_question or title).lower()
        
        # Try to find a good label column (for X-axis) by analyzing user question
        if x_column is None:
            # Build candidates based on what user is asking about
            label_candidates = []
            
            # Look for keywords in question to determine focus
            # Only add candidates that actually exist in the data
            if "app" in question_lower and "app_id" in columns:
                label_candidates.append("app_id")
            if ("media" in question_lower or "source" in question_lower) and "media_source" in columns:
                label_candidates.append("media_source")
            if "partner" in question_lower and "partner" in columns:
                label_candidates.append("partner")
            if "engagement" in question_lower and "engagement_type" in columns:
                label_candidates.append("engagement_type")
            if "site" in question_lower and "site_id" in columns:
                label_candidates.append("site_id")
            
            # Add all string/non-numeric columns as fallback (these are good for X-axis)
            for col in columns:
                if col not in label_candidates:
                    sample_val = rows[0].get(col)
                    if not isinstance(sample_val, (int, float)) or isinstance(sample_val, bool):
                        if col != "_rid":  # Skip internal columns only
                            label_candidates.append(col)
            
            # Find first matching column
            x_column = label_candidates[0] if label_candidates else columns[0]
        
        # Try to find a good numeric column (for Y-axis)
        if y_column is None:
            numeric_candidates = ["total_clicks", "total_events", "clicks", "click_count", "count", "total", "value", "metric"]
            # First check for explicit numeric column names (exclude hr, which is just the hour number)
            y_column = next((col for col in numeric_candidates if col in columns), None)
            
            # If not found, find first numeric column
            if y_column is None:
                def _to_float(v):
                    try:
                        if v is None or isinstance(v, bool):
                            return None
                        return float(v)
                    except Exception:
                        return None

                best_col = None
                best_range = -1.0
                for col in columns:
                    if col == x_column:
                        continue
                    vals = [_to_float(r.get(col)) for r in rows[:50]]
                    vals = [v for v in vals if v is not None]
                    if not vals:
                        continue
                    col_range = max(vals) - min(vals)
                    if col_range > best_range:
                        best_range = col_range
                        best_col = col

                y_column = best_col
            
            # Fallback
            if y_column is None:
                y_column = columns[1] if len(columns) > 1 else columns[0]
    
    # Detect if user asked for "top N" in the title
    import re
    top_n_match = re.search(r'\btop\s+(\d+)\b', title.lower())
    limit = int(top_n_match.group(1)) if top_n_match else 50
    
    # Aggregate by label: sum metric per x, then sort desc and keep top N
    def _safe_float(v):
        try:
            if v is None or isinstance(v, bool):
                return 0.0
            return float(v)
        except Exception:
            return 0.0

    from collections import defaultdict

    agg = defaultdict(float)
    for row in rows:
        x_val = str(row.get(x_column, ""))
        y_val = _safe_float(row.get(y_column))
        agg[x_val] += y_val

    pairs = sorted(agg.items(), key=lambda p: p[1], reverse=True)[:limit]

    # If all values identical or zero, fallback to frequency count of x_column
    if pairs:
        ys = [p[1] for p in pairs]
        if max(ys) == min(ys):
            from collections import Counter
            counts = Counter(str(row.get(x_column, "")) for row in rows)
            pairs = [(k, float(v)) for k, v in counts.most_common(limit)]

    x_values = [p[0] for p in pairs]
    y_values = [p[1] for p in pairs]

    base_opts = {
        "title": {"text": title},
        "tooltip": {"trigger": "axis"},
        "grid": {"left": "10%", "right": "10%", "bottom": "10%", "containLabel": True},
    }

    try:
        if chart_type.lower() == "pie":
            return {
                **base_opts,
                "series": [
                    {
                        "type": "pie",
                        "radius": ["40%", "75%"],
                        "data": [{"name": x_values[i], "value": y_values[i]} for i in range(len(x_values))],
                    }
                ],
            }
        if chart_type.lower() == "line":
            return {
                **base_opts,
                "xAxis": {"type": "category", "data": x_values},
                "yAxis": {"type": "value"},
                "series": [
                    {
                        "type": "line",
                        "data": y_values,
                        "smooth": True,
                    }
                ],
            }
        # default bar
        return {
            **base_opts,
            "xAxis": {"type": "category", "data": x_values},
            "yAxis": {"type": "value"},
            "series": [
                {
                    "type": "bar",
                    "data": y_values,
                }
            ],
        }
    except Exception:
        return {}


def rows_to_chart_html(
    rows: List[Dict[str, Any]],
    chart_type: str = "bar",
    x_column: Optional[str] = None,
    y_column: Optional[str] = None,
    title: str = "Chart"
) -> str:
    """
    Convert tabular data (list of dicts) to pyecharts HTML.
    
    Args:
        rows: List of dictionaries with data
        chart_type: "bar", "line", or "pie"
        x_column: Column name for X-axis (auto-detect if None)
        y_column: Column name for Y-axis (auto-detect if None)
        title: Chart title
    
    Returns:
        HTML string from pyecharts
    """
    if not rows:
        return "<p>No data to visualize</p>"
    
    # Auto-detect columns if not provided
    if x_column is None or y_column is None:
        columns = list(rows[0].keys())
        if x_column is None:
            x_column = columns[0]  # First column is usually labels
        if y_column is None:
            y_column = columns[1] if len(columns) > 1 else columns[0]
    
    # Extract values
    x_values = [str(row.get(x_column, "")) for row in rows[:50]]  # Limit to 50 rows
    y_values = []
    for row in rows[:50]:
        val = row.get(y_column)
        # Try to convert to number if possible
        try:
            y_values.append(float(val) if val is not None else 0)
        except (ValueError, TypeError):
            y_values.append(0)
    
    # Generate chart based on type
    try:
        if chart_type.lower() == "pie":
            chart = Pie()
            chart.add(
                "",
                [(x_values[i], y_values[i]) for i in range(len(x_values))],
                radius=["40%", "75%"]
            )
        elif chart_type.lower() == "line":
            chart = Line()
            chart.add_xaxis(x_values)
            chart.add_yaxis("", y_values, smooth=True)
        else:  # bar (default)
            chart = Bar()
            chart.add_xaxis(x_values)
            chart.add_yaxis("", y_values)
        
        chart.set_global_opts(
            title_opts=opts.TitleOpts(title=title),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
        )
        
        return chart.render_embed()
    
    except Exception as e:
        return f"<p>Error generating chart: {str(e)}</p>"


def auto_chart_type(user_question: str, data: List[Dict[str, Any]]) -> str:
    """
    Suggest chart type based on user question and data.
    Returns: "bar", "line", or "pie"
    """
    question_lower = user_question.lower()
    
    # Check for distribution (pie chart)
    if any(word in question_lower for word in ["distribution", "proportion", "breakdown", "percentage", "%"]):
        return "pie"
    
    # Check for trends (line chart)
    if any(word in question_lower for word in ["trend", "over time", "daily", "hourly", "evolution", "growth"]):
        return "line"
    
    # Default to bar
    return "bar"
