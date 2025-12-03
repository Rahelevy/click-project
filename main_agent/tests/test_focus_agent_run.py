from main_agent.sub_agents.b_focus_agent.agent import FocusAgent
from main_agent.sub_agents.b_focus_agent.schemas import AgentBInput


def run_focus_test(original_question: str, refined_question=None):
    print("\n" + "=" * 80)
    print(f"ORIGINAL QUESTION: {original_question}")
    print(f"REFINED QUESTION:  {refined_question}")
    print("=" * 80)

    agent = FocusAgent()

    state = AgentBInput(
        original_question=original_question,
        refined_question=refined_question,
        reason="manual_test"
    )

    try:
        result = agent.run(state)
    except Exception as e:
        print("❌ Agent crashed with exception:")
        print(e)
        return

    print("\nRAW RESULT:")
    print(result)

    out = result.get("state")
    print("\nPARSED STATE:")
    print(out)

    # ---- basic validations (soft asserts) ----
    if out.failed:
        print("\n⚠️ Agent returned failed=True")
        print("error_message:", out.error_message)
        return

    # rule: can't return both refined_question and question_to_user
    if out.refined_question and out.question_to_user:
        print("\n❌ INVALID OUTPUT: both refined_question and question_to_user are set!")
        return

    if out.awaiting_user_input:
        if not out.question_to_user:
            print("\n❌ INVALID OUTPUT: awaiting_user_input=True but question_to_user is empty")
            return
        print("\n✅ CASE 2 detected: agent asks user for missing info.")
        print("missing_fields:", out.missing_fields)
        print("question_to_user:", out.question_to_user)

    else:
        if not out.refined_question:
            print("\n❌ INVALID OUTPUT: awaiting_user_input=False but refined_question is empty")
            return
        print("\n✅ CASE 1 detected: agent finished refinement.")
        print("refined_question:", out.refined_question)

    print("\n✅ FocusAgent test finished OK.")


if __name__ == "__main__":
    # ----------- Example runs -----------
    # 1) Should usually be CASE 1 (already enough filters)
    run_focus_test("show me all the clicks for app id 20 on october 2025")

    # 2) Should usually be CASE 2 (missing filters)
    run_focus_test("show me all the clicks")

    # 3) Another missing-fields example
    run_focus_test("clicks for facebook campaign yesterday")


