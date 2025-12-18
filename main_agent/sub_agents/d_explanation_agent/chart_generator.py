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
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        if chart_type == "pie":
            # Pie chart
            ax.pie(y_data, labels=x_data, autopct='%1.1f%%', startangle=90)
        elif chart_type == "line":
            # Line chart
            ax.plot(x_data, y_data, marker='o', linewidth=2, markersize=6)
            ax.set_ylabel("Value")
            ax.grid(True, alpha=0.3)
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
        
        return f"![Chart](data:image/png;base64,{img_base64})"
    
    except Exception as e:
        print(f"Error converting chart to PNG: {e}")
        return None


def rows_to_echarts_options(
    rows: List[Dict[str, Any]],
    chart_type: str = "bar",
    x_column: Optional[str] = None,
    y_column: Optional[str] = None,
    title: str = "Chart"
) -> Dict[str, Any]:
    """Convert tabular data to a plain ECharts options dict (no HTML/JS)."""
    if not rows:
        return {}

    # Auto-detect columns
    if x_column is None or y_column is None:
        columns = list(rows[0].keys())
        if x_column is None:
            x_column = columns[0]
        if y_column is None:
            y_column = columns[1] if len(columns) > 1 else columns[0]

    x_values = [str(row.get(x_column, "")) for row in rows[:50]]
    y_values: List[float] = []
    for row in rows[:50]:
        val = row.get(y_column)
        try:
            y_values.append(float(val) if val is not None else 0.0)
        except (ValueError, TypeError):
            y_values.append(0.0)

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
