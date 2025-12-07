import json
from main_agent.sub_agents.a_intent_agent.agent import IntentAgent
from main_agent.sub_agents.a_intent_agent.schemas import AgentAOutput


# --------------------------------------------------------------------
# Helper to run the agent safely and print results
# --------------------------------------------------------------------
def run_test(test_name: str, user_question: str):
    print("\n" + "=" * 80)
    print(f"TEST: {test_name}")
    print("=" * 80)

    agent = IntentAgent()

    # Initialize state correctly
    state = AgentAOutput(
        valid=False,
        question=user_question,
        sql=None
    )

    # Run agent
    result = agent.run(state)

    # Convert Pydantic → dict for safe printing
    safe_result = result.copy()
    safe_result["state"] = safe_result["state"].model_dump()

    print(json.dumps(safe_result, ensure_ascii=False, indent=2))

    return safe_result


# --------------------------------------------------------------------
# TEST 1 — NO FULL SELECT (ENGLISH)
# --------------------------------------------------------------------
def test_no_full_select_english():
    question = (
        "Show me retargeting clicks for app_id com.app.test between 2025-01-01 and 2025-01-31"
    )
    result = run_test("NO FULL SELECT (ENGLISH)", question)

    assert result["state"]["valid"]
    sql = result["state"]["sql"]
    assert "SELECT SUM(total_events)" in sql
    assert "event_time" not in sql.split("SELECT")[1].split("FROM")[0]


# --------------------------------------------------------------------
# TEST 2 — NO FULL SELECT (HEBREW)
# --------------------------------------------------------------------
def test_no_full_select_hebrew():
    question = "תראה לי קליקים של ריטרגטינג עבור האפליקציה com.app.test בין 2025-01-01 ל-2025-01-31"
    result = run_test("NO FULL SELECT (HEBREW)", question)

    assert result["state"]["valid"]
    sql = result["state"]["sql"]
    assert "SELECT SUM(total_events)" in sql


# --------------------------------------------------------------------
# TEST 3 — reversed date range auto fix
# --------------------------------------------------------------------
def test_reversed_date_range():
    question = "Show me clicks from 2025-10-10 to 2025-01-01 for app_id test.app"
    result = run_test("REVERSED DATE RANGE AUTO-FIX", question)

    assert result["state"]["valid"]
    sql = result["state"]["sql"]
    assert "2025-01-01" in sql
    assert "2025-10-11" in sql  # end +1 day


# --------------------------------------------------------------------
# TEST 4 — language check (Hebrew)
# --------------------------------------------------------------------
def test_language_hebrew():
    question = "תן לי את כל הדאטה"
    result = run_test("LANGUAGE CHECK (HEBREW)", question)

    assert not result["state"]["valid"]

    q = result["state"]["question_to_user"]
    assert any("א" <= ch <= "ת" for ch in q), "Expected Hebrew output"


# --------------------------------------------------------------------
# TEST 5 — language check (English)
# --------------------------------------------------------------------
def test_language_english():
    question = "Give me all the data for the last day were the app id=2"
    result = run_test("LANGUAGE CHECK (ENGLISH)", question)

    assert not result["state"]["valid"]

    q = result["state"]["question_to_user"]
    assert any("a" <= ch.lower() <= "z" for ch in q), "Expected English output"


# --------------------------------------------------------------------
# TEST 6 — unsupported field (no reason check!)
# --------------------------------------------------------------------
def test_unsupported_field():
    question = "Show me installs in France"
    result = run_test("UNSUPPORTED FIELD", question)

    assert not result["state"]["valid"]
    assert result["state"]["awaiting_user_input"]
    assert result["state"]["question_to_user"] is not None


# --------------------------------------------------------------------
# TEST 7 — fallback JSON (Hebrew)
# --------------------------------------------------------------------
def test_fallback_hebrew():
    question = "תן לי בבקשה"
    result = run_test("HEBREW FALLBACK", question)

    assert not result["state"]["valid"]

    q = result["state"]["question_to_user"]
    assert any("א" <= ch <= "ת" for ch in q), "Fallback should be Hebrew"


# --------------------------------------------------------------------
# TEST 8 — fallback JSON (English)
# --------------------------------------------------------------------
def test_fallback_english():
    question = "Please show me"
    result = run_test("ENGLISH FALLBACK", question)

    assert not result["state"]["valid"]

    q = result["state"]["question_to_user"]
    assert any("a" <= ch.lower() <= "z" for ch in q), "Fallback should be English"


# --------------------------------------------------------------------
# Run all tests
# --------------------------------------------------------------------
if __name__ == "__main__":
    test_no_full_select_english()
    test_no_full_select_hebrew()
    test_reversed_date_range()
    test_language_hebrew()
    test_language_english()
    test_unsupported_field()
    test_fallback_hebrew()
    test_fallback_english()

