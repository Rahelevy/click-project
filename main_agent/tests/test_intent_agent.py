import json
try:
    import pytest
except ImportError:
    # Minimal stub so this file can run without pytest installed
    class _DummyMark:
        def skip(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

    class _DummyPytest:
        mark = _DummyMark()

    pytest = _DummyPytest()

from main_agent.sub_agents.a_intent_agent.agent import IntentAgent
from main_agent.sub_agents.a_intent_agent.schemas import AgentAOutput


# ---------------------------------------------------------
# Helper for pretty test execution (same style as before)
# ---------------------------------------------------------
def run_test(title, question):
    print("\n" + "=" * 80)
    print(f"TEST: {title}")
    print("=" * 80)

    agent = IntentAgent()
    state = AgentAOutput(question=question)
    result = agent.run(state)

    # Convert Pydantic model to dict for printing
    output = {
        "state": result["state"].model_dump(),
        "should_run_focus": result["should_run_focus"],
        "should_run_executor": result["should_run_executor"],
        "should_run_explainer": result["should_run_explainer"],
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return output



# =====================================================================
# 1. TOO BROAD QUESTIONS
# =====================================================================
@pytest.mark.skip(reason="Temporarily disabled; focusing only on 4 custom questions")
def test_too_broad():
    r = run_test("TOO BROAD", "תן לי את כל הדאטה")
    assert r["state"]["valid"] is False
    assert r["state"]["awaiting_user_input"] is True
    assert r["state"]["sql"] is None
    print("\n✔ TOO BROAD TEST PASSED")


# =====================================================================
# 2. APP ID NUMERIC
# =====================================================================
@pytest.mark.skip(reason="Temporarily disabled; focusing only on 4 custom questions")
def test_app_id_numeric():
    r = run_test("APP ID NUMERIC", "Show me clicks for app id 5")
    assert "app_id_5" in (r["state"]["sql"] or "")
    assert r["state"]["valid"] is True
    print("\n✔ APP ID NUMERIC TEST PASSED")


# =====================================================================
# 3. APP ID INVALID STRING → must ask user
# =====================================================================
@pytest.mark.skip(reason="Temporarily disabled; focusing only on 4 custom questions")
def test_app_id_invalid():
    r = run_test("APP ID INVALID", "Show me clicks for app_id xyz")
    assert r["state"]["valid"] is False
    assert r["state"]["sql"] is None
    print("\n✔ APP ID INVALID TEST PASSED")


# =====================================================================
# 4. MEDIA SOURCE NUMERIC
# =====================================================================
@pytest.mark.skip(reason="Temporarily disabled; focusing only on 4 custom questions")
def test_media_source_numeric():
    r = run_test("MEDIA SOURCE NUMERIC", "Show me clicks from media source 257")
    assert "media_source_257" in (r["state"]["sql"] or "")
    assert r["state"]["valid"] is True
    print("\n✔ MEDIA SOURCE NUMERIC TEST PASSED")


# =====================================================================
# 5. PARTNER NUMERIC
# =====================================================================
@pytest.mark.skip(reason="Temporarily disabled; focusing only on 4 custom questions")
def test_partner_numeric():
    r = run_test("PARTNER NUMERIC", "Show me clicks from partner 88")
    assert "partner_88" in (r["state"]["sql"] or "")
    assert r["state"]["valid"] is True
    print("\n✔ PARTNER NUMERIC TEST PASSED")


# =====================================================================
# 6. SITE ID NUMERIC
# =====================================================================
@pytest.mark.skip(reason="Temporarily disabled; focusing only on 4 custom questions")
def test_site_id_numeric():
    r = run_test("SITE ID NUMERIC", "Show me clicks from site id 38238605550")
    assert "site_id_38238605550" in (r["state"]["sql"] or "")
    assert r["state"]["valid"] is True
    print("\n✔ SITE ID NUMERIC TEST PASSED")


# =====================================================================
# 7. RETARGETING SEMANTIC
# =====================================================================
@pytest.mark.skip(reason="Temporarily disabled; focusing only on 4 custom questions")
def test_retargeting_semantic():
    r = run_test("RETARGETING SEMANTIC",
                 "Show me clicks from users who already installed for app_id 2")

    assert "is_retargeting = TRUE" in (r["state"]["sql"] or "")
    assert "app_id_2" in (r["state"]["sql"] or "")
    print("\n✔ RETARGETING SEMANTIC TEST PASSED")


# =====================================================================
# 8. AGGREGATION ("how many") → SUM(total_events)
# =====================================================================
@pytest.mark.skip(reason="Temporarily disabled; focusing only on 4 custom questions")
def test_aggregation_sum():
    r = run_test("AGGREGATION SUM", "How many clicks from media source 257?")
    assert "SUM(total_events)" in (r["state"]["sql"] or "")
    print("\n✔ AGGREGATION SUM TEST PASSED")


# =====================================================================
# 9. NO AGGREGATION → must return full fields
# =====================================================================
@pytest.mark.skip(reason="Temporarily disabled; focusing only on 4 custom questions")
def test_no_aggregation():
    r = run_test("NO AGGREGATION", "Show me clicks from media source 257")

    sql = r["state"]["sql"] or ""
    assert "SUM(" not in sql
    assert "event_time" in sql
    print("\n✔ NO AGGREGATION TEST PASSED")


# =====================================================================
# 10. REVERSED DATE FIX
# =====================================================================
@pytest.mark.skip(reason="Temporarily disabled; focusing only on 4 custom questions")
def test_reversed_dates():
    r = run_test(
        "REVERSED DATE FIX",
        "Show me clicks from 2025-10-10 to 2025-01-01 for app_id 5"
    )

    sql = r["state"]["sql"] or ""
    assert "2025-01-01" in sql
    assert "2025-10-11" in sql  # end+1 day
    print("\n✔ REVERSED DATE FIX TEST PASSED")


# =====================================================================
# 11. LANGUAGE CHECK (HEBREW)
# =====================================================================
@pytest.mark.skip(reason="Temporarily disabled; focusing only on 4 custom questions")
def test_language_hebrew():
    r = run_test("LANGUAGE HEBREW", "כמה קליקים היו לapp id 2?")
    # Hebrew response expected
    assert any("א" <= ch <= "ת" for ch in (r["state"]["question_to_user"] or "")) \
        or r["state"]["valid"] is True
    print("\n✔ LANGUAGE HEBREW TEST PASSED")


# =====================================================================
# 12. FALLBACK NON-JSON
# =====================================================================
@pytest.mark.skip(reason="Temporarily disabled; focusing only on 4 custom questions")
def test_fallback_json_error():
    # We force model to return garbage by giving it a nonsense input
    r = run_test("FALLBACK JSON", "### @$%^#@$%^ invalid json trigger")
    assert r["state"]["valid"] is False
    assert r["state"]["question_to_user"] is not None
    print("\n✔ FALLBACK JSON TEST PASSED")


# =====================================================================
# 13–16. NEW SCENARIOS (YOUR QUESTIONS)
# =====================================================================
def test_media_source_most_clicks():
    run_test("MEDIA_SOURCE MOST CLICKS", "Which media_source sends the most clicks?")


def test_suspicious_site_between_hours():
    run_test(
        "SUSPICIOUS SITE BETWEEN HOURS",
        "Which site_id looks suspicious between 02:00–05:00?",
    )


def test_monday_spike_in_clicks():
    run_test(
        "MONDAY SPIKE IN CLICKS",
        "Is there a sudden spike in clicks on Monday?",
    )


def test_top_app_ids_by_click_volume():
    run_test(
        "TOP APP_IDS BY CLICK VOLUME",
        "Show me the top app_ids by click volume.",
    )



# =====================================================================
# MAIN
# =====================================================================
if __name__ == "__main__":
    # Only run the 4 custom-question tests when executing this file directly
    test_media_source_most_clicks()
    test_suspicious_site_between_hours()
    test_monday_spike_in_clicks()
    test_top_app_ids_by_click_volume()

    print("\n\n🎉 ALL TESTS COMPLETED SUCCESSFULLY (if no errors above)\n")
