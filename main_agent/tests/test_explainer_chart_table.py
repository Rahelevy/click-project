from main_agent.sub_agents.d_explanation_agent.agent import ExplainerAgent
from main_agent.sub_agents.d_explanation_agent.schemas import ExplanationInput, ExecutorResult


def mock_table_generator(user_question: str, incoming_json: str):
    # Simulate LLM JSON output for a table
    return {
        "status": "success",
        "description": "Click summary:",
        "render_type": "table",
        "table_markdown": (
            "Click summary:\n\n"
            "| date | clicks |\n"
            "|---|---|\n"
            "| 2025-03-01 | 10 |\n"
            "| 2025-03-02 | 12 |\n"
        ),
        "chart_options": None,
    }


def mock_chart_generator(user_question: str, incoming_json: str):
    # Simulate LLM JSON output for an ECharts bar chart
    return {
        "status": "success",
        "description": "Clicks by day",
        "render_type": "chart",
        "table_markdown": None,
        "chart_options": {
            "title": {"text": "Clicks by day"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": ["2025-03-01", "2025-03-02"]},
            "yAxis": {"type": "value"},
            "series": [
                {"name": "Clicks", "type": "bar", "data": [10, 12]}
            ],
        },
    }


def test_explainer_table_output():
    agent = ExplainerAgent(response_generator=mock_table_generator)
    state = ExplanationInput(
        user_question="Show me clicks per day as a table",
        incoming=ExecutorResult(
            status="success",
            description='[{"date":"2025-03-01","clicks":10},{"date":"2025-03-02","clicks":12}]'
        ),
    )

    result = agent.run(state)
    out = result["state"]
    assert out.status == "success"
    assert out.render_type == "table"
    assert out.table_markdown is not None
    assert "|---|---|" in out.table_markdown
    assert "2025-03-01" in out.table_markdown


def test_explainer_chart_output():
    agent = ExplainerAgent(response_generator=mock_chart_generator)
    state = ExplanationInput(
        user_question="Graph clicks per day",
        incoming=ExecutorResult(
            status="success",
            description='[{"date":"2025-03-01","clicks":10},{"date":"2025-03-02","clicks":12}]'
        ),
    )

    result = agent.run(state)
    out = result["state"]
    assert out.status == "success"
    assert out.render_type == "chart"
    assert out.chart_options is not None
    assert out.chart_options.get("series")[0].get("type") in ("bar", "line")
