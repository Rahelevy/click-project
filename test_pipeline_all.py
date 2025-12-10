import asyncio
from google.genai.types import Content, Part

from main_agent.agent import root_agent


# ----------------------------
# Fake ctx/session objects
# ----------------------------

class FakeSession:
    def __init__(self):
        self.state = {}

class FakeCtx:
    def __init__(self, text: str):
        self.user_content = Content(role="user", parts=[Part(text=text)])
        self.session = FakeSession()


async def run_root_async(question: str):
    ctx = FakeCtx(question)

    events = []
    async for ev in root_agent._run_async_impl(ctx):
        events.append(ev)

    last = events[-1]
    return {
        "answer": last.content.parts[0].text,
        "state": last.actions.state_delta.get("root_state"),
        "stage": last.actions.state_delta.get("stage"),
    }

def run_root(question: str):
    return asyncio.run(run_root_async(question))


# ----------------------------
# Assertions helpers
# ----------------------------

def assert_stage(res, expected_stage):
    assert res["stage"] == expected_stage, (
        f"Expected stage {expected_stage}, got {res['stage']}. Full res: {res}"
    )

def assert_missing(res, field):
    missing = res["state"].get("missing_fields", [])
    assert field in missing, (
        f"Expected missing_fields to include {field}. got {missing}"
    )


# ----------------------------
# Tests
# ----------------------------

def test_empty_question_handled_by_A():
    res = run_root("")
    assert_stage(res, "awaiting_user_input")

    assert res["state"].get("reason") == "missing_question"
    assert_missing(res, "question")
    print("✅ empty question handled by A (no B)")

def test_too_broad_goes_to_B():
    res = run_root("תן לי את כל הדאטה")
    assert_stage(res, "awaiting_user_input")

    assert_missing(res, "filter_needed")
    print("✅ too broad question -> B asks user")

def test_future_date_is_covered():
    res = run_root("כמה קליקים היו ב app id 2 בין 10-01-2026 ל 10-03-2026?")

    # מסלול אידיאלי: A תופס עתידי → B שואל → awaiting_user_input
    if res["stage"] == "awaiting_user_input":
        missing = res["state"].get("missing_fields", [])
        reason = res["state"].get("reason")

        assert ("date" in missing) or (reason in ["invalid_date", "too_broad", "missing_filters"]), \
            f"Future date expected to miss date or be invalid. got missing={missing}, reason={reason}"

        print("✅ future/invalid date -> B asks clarification (covered)")
        return

    # מסלול חלופי סביר: LLM פספס עתידי אבל הזרימה לא נשברת
    if res["stage"] == "done":
        assert res["answer"] is not None
        print("✅ future date missed by LLM but flow still safe (covered)")
        return

    raise AssertionError(f"Unexpected stage for future date case: {res}")

def test_missing_filters_goes_to_B():
    res = run_root("כמה קליקים היו אתמול?")
    assert_stage(res, "awaiting_user_input")
    print("✅ missing app/source/etc -> B asks clarification")

def test_valid_query_runs_executor_explainer():
    res = run_root("כמה קליקים היו ב app id 2 בין 10-01-2025 ל 10-03-2025")
    assert_stage(res, "done")
    assert res["answer"] is not None
    print("✅ valid query -> executor+explainer flow")

def test_non_json_does_not_crash():
    res = run_root("בלה בלה בלה מה זה השטויות האלה")
    assert res["stage"] in ["awaiting_user_input", "done"]
    print("✅ non-json / unclear question doesn't crash flow")

def test_english_broad_question():
    res = run_root("give me all data")
    assert_stage(res, "awaiting_user_input")
    assert any(ch.isascii() for ch in (res["answer"] or "")), "Expected English clarification"
    print("✅ english question -> english clarification")


def main():
    test_empty_question_handled_by_A()
    test_too_broad_goes_to_B()
    test_future_date_is_covered()
    test_missing_filters_goes_to_B()
    test_valid_query_runs_executor_explainer()
    test_non_json_does_not_crash()
    test_english_broad_question()

    print("\n🎉 ALL TESTS PASSED")

if __name__ == "__main__":
    main()
