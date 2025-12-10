# test_pipeline_all.py
import asyncio

from main_agent.agent import root_agent  # אצלך root_agent מוגדר ב-main_agent/agent.py


# ----------------------------
# Fakes that mimic ADK objects
# ----------------------------
class FakePart:
    def __init__(self, text: str):
        self.text = text


class FakeContent:
    def __init__(self, text: str):
        self.parts = [FakePart(text)]


class FakeSession:
    def __init__(self):
        self.state = {}  # Root משתמש בזה לשמירת root_state


class FakeCtx:
    def __init__(self, text: str):
        self.user_content = FakeContent(text)
        self.session = FakeSession()


def run_root(text: str):
    """Helper to run run_pipeline synchronously."""
    ctx = FakeCtx(text)
    session_state = ctx.session.state.get("root_state", {})
    return root_agent.run_pipeline(ctx, session_state)


# ----------------------------
# Tests
# ----------------------------
def test_empty_question():
    # A אמור לטפל לבד ולהחזיר awaiting_user_input=True
    res = run_root("")
    assert res["stage"] == "awaiting_user_input"
    assert "לא קיבלתי שאלה" in res["answer"] or "didn't get a question" in res["answer"]
    print("✅ empty question handled by A (no B)")

def test_too_broad_question():
    # A שולח ל-B, B שואל שאלה ממוקדת
    res = run_root("תן לי את כל הדאטה")
    assert res["stage"] == "awaiting_user_input"
    assert res["state"].get("missing_fields") == ["filter_needed"]
    assert res["state"].get("question_to_user")  # B חייב לשאול משהו
    print("✅ too broad question -> B asks user")

def test_valid_query_runs_executor():
    # שאלה תקינה עם פילטרים + תאריך בעבר (2025-09 זה בעבר יחסית ל-2025-12)
    res = run_root("כמה קליקים היו ב app id 2 בין 09-01-2025 ל 09-03-2025?")
    # אמור להגיע ל-done (Executor+Explainer)
    assert res["stage"] == "done"
    assert isinstance(res["answer"], str) and len(res["answer"]) > 0
    print("✅ valid query -> executor+explainer flow")

def test_future_date_goes_to_B():
    # A מזהה תאריך עתידי -> valid=False, missing_fields כולל date, שולח ל-B
    res = run_root("כמה קליקים היו ב app id 2 בין 10-01-2026 ל 10-03-2026?")
    assert res["stage"] == "awaiting_user_input"
    assert "date" in res["state"].get("missing_fields", [])
    print("✅ future/invalid date -> B asks clarification")

def test_missing_app_id_goes_to_B():
    # חסר app_id -> A אמור לשלוח ל-B שיבקש
    res = run_root("כמה קליקים היו אתמול?")
    assert res["stage"] == "awaiting_user_input"
    assert res["state"].get("missing_fields")  # לא ריק
    print("✅ missing app/source/etc -> B asks clarification")

def test_non_json_model_output_fallback():
    # קשה לדמות LLM לא-JSON בלי למוק את Gemini,
    # אז רק בודקים שה-root לא מתפוצץ על שאלה לא ברורה
    res = run_root("בלה בלה משהו לא ברור")
    assert res["stage"] in ["awaiting_user_input", "done"]
    print("✅ non-json / unclear question doesn't crash flow")

def test_english_flow_language():
    res = run_root("give me all data")
    assert res["stage"] == "awaiting_user_input"
    # B אמור לשאול באנגלית
    assert "What" in res["answer"] or "which" in res["answer"].lower()
    print("✅ english question -> english clarification")

# ----------------------------
# Runner
# ----------------------------
def main():
    test_empty_question()
    test_too_broad_question()
    test_valid_query_runs_executor()
    test_future_date_goes_to_B()
    test_missing_app_id_goes_to_B()
    test_non_json_model_output_fallback()
    test_english_flow_language()

    print("\n🎉 ALL TESTS PASSED")

if __name__ == "__main__":
    main()
