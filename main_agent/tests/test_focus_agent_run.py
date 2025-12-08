# from main_agent.sub_agents.b_focus_agent.agent import FocusAgent
# from main_agent.sub_agents.b_focus_agent.schemas import AgentBInput


# def run_focus_test(original_question: str, refined_question=None):
#     print("\n" + "=" * 80)
#     print(f"ORIGINAL QUESTION: {original_question}")
#     print(f"REFINED QUESTION:  {refined_question}")
#     print("=" * 80)

#     agent = FocusAgent()

#     state = AgentBInput(
#         original_question=original_question,
#         refined_question=refined_question,
#         reason="manual_test"
#     )

#     try:
#         result = agent.run(state)
#     except Exception as e:
#         print("❌ Agent crashed with exception:")
#         print(e)
#         return

#     print("\nRAW RESULT:")
#     print(result)

#     out = result.get("state")
#     print("\nPARSED STATE:")
#     print(out)

#     # ---- basic validations (soft asserts) ----
#     if out.failed:
#         print("\n⚠️ Agent returned failed=True")
#         print("error_message:", out.error_message)
#         return

#     # rule: can't return both refined_question and question_to_user
#     if out.refined_question and out.question_to_user:
#         print("\n❌ INVALID OUTPUT: both refined_question and question_to_user are set!")
#         return

#     if out.awaiting_user_input:
#         if not out.question_to_user:
#             print("\n❌ INVALID OUTPUT: awaiting_user_input=True but question_to_user is empty")
#             return
#         print("\n✅ CASE 2 detected: agent asks user for missing info.")
#         print("missing_fields:", out.missing_fields)
#         print("question_to_user:", out.question_to_user)

#     else:
#         if not out.refined_question:
#             print("\n❌ INVALID OUTPUT: awaiting_user_input=False but refined_question is empty")
#             return
#         print("\n✅ CASE 1 detected: agent finished refinement.")
#         print("refined_question:", out.refined_question)

#     print("\n✅ FocusAgent test finished OK.")


# if __name__ == "__main__":
#     # ----------- Example runs -----------
#     # 1) Should usually be CASE 1 (already enough filters)
#     run_focus_test("show me all the clicks for app id 20 on october 2025")

#     # 2) Should usually be CASE 2 (missing filters)
#     run_focus_test("show me all the clicks")

#     # 3) Another missing-fields example
#     run_focus_test("clicks for facebook campaign yesterday")


from main_agent.sub_agents.b_focus_agent.agent import FocusAgent
from main_agent.sub_agents.b_focus_agent.schemas import AgentBInput


def run_focus_test(original_question: str, refined_question=None):
    print("\n" + "=" * 80)
    print(f"ORIGINAL QUESTION: {repr(original_question)}")
    print(f"REFINED QUESTION:  {repr(refined_question)}")
    print("=" * 80)

    agent = FocusAgent()

    state = AgentBInput(
        original_question=original_question,
        refined_question=refined_question,
        reason="manual_test",
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
    # ------------------------------------------------------------------
    # GROUP 0 – EMPTY / INVALID QUESTIONS
    # ------------------------------------------------------------------
    run_focus_test("")                       # completely empty
    run_focus_test(" ")                      # whitespace only
    run_focus_test("?")                      # symbol only
    run_focus_test("תעשו לי דוח")           # too vague
    run_focus_test("תראי לי נתונים")        # too vague

    # ------------------------------------------------------------------
    # GROUP 1 – VERY GENERAL, NO FILTERS
    # ------------------------------------------------------------------
    run_focus_test("show me all the data")
    run_focus_test("I want to see all events")
    run_focus_test("אני רוצה לראות את כל הקליקים והצפיות")
    run_focus_test("כמה אירועים יש לנו בסך הכל?")

    # ------------------------------------------------------------------
    # GROUP 2 – MISSING TIME FILTER (event_time)
    # ------------------------------------------------------------------
    run_focus_test("how many clicks did app_id_13 get?")
    run_focus_test("which media_source has the most events?")
    run_focus_test("who is the strongest partner by total_events?")
    run_focus_test("what is the most common engagement_type for app_id_2?")
    run_focus_test("how many events does partner_507 have?")

    # ------------------------------------------------------------------
    # GROUP 3 – MISSING app_id BUT HAS OTHER FILTERS
    # ------------------------------------------------------------------
    run_focus_test("how many total_events did we have between 2025-10-01 and 2025-10-07?")
    run_focus_test("show me the top media_source in the last week")
    run_focus_test("how many events came from partner_194 yesterday?")
    run_focus_test("how many clicks from retargeting campaigns did we have at 18:00?")

    # ------------------------------------------------------------------
    # GROUP 4 – MISSING BOTH app_id AND TIME (VERY OPEN)
    # ------------------------------------------------------------------
    run_focus_test("which media_source are the best?")
    run_focus_test("which site_id looks the most suspicious?")
    run_focus_test("for which partner do we see the most view-only traffic (is_engaged_view=true)?")

    # ------------------------------------------------------------------
    # GROUP 5 – AMBIGUOUS / BUSINESS-MEANING UNCLEAR
    # ------------------------------------------------------------------
    run_focus_test("who is the most problematic partner in our campaigns?")
    run_focus_test("where do you see strange behaviour in the data?")
    run_focus_test("find anomalies in our partners")
    run_focus_test("show me places that look like fraud")

    # ------------------------------------------------------------------
    # GROUP 6 – MULTI-GOAL QUESTIONS (TOO MANY TARGETS)
    # ------------------------------------------------------------------
    run_focus_test("show me the media_source with the most total_events and also the partner with the fewest")
    run_focus_test("I want a breakdown by hour and by app_id and by site_id")
    run_focus_test("give me a general summary for all apps and partners for the last month")

    # ------------------------------------------------------------------
    # GROUP 7 – CONTRADICTING FILTERS
    # ------------------------------------------------------------------
    run_focus_test("show me events for app_id_13 but only where is_retargeting=false and users came back again")
    run_focus_test("I only want views (is_engaged_view=true) but they must be clicks")
    run_focus_test("show me all media_source that have zero total_events")

    # ------------------------------------------------------------------
    # GROUP 8 – USING NON-EXISTING FIELDS
    # ------------------------------------------------------------------
    run_focus_test("how many clicks did we get for app_name 'Candy Crush'?")  # app_name not in schema
    run_focus_test("break it down by country")                               # country not in schema
    run_focus_test("show me a report by device_type")                        # device_type not in schema
    run_focus_test("how many unique users did we have?")                     # no user_id

    # ------------------------------------------------------------------
    # GROUP 9 – FOLLOW-UP / CONTEXT-DEPENDENT QUESTIONS
    # (these are good to see if the model wrongly assumes context)
    # ------------------------------------------------------------------
    run_focus_test("do the same but just for last week")
    run_focus_test("and what about a different partner?")
    run_focus_test("now show me only what you said looked suspicious")

    # ------------------------------------------------------------------
    # GROUP 10 – MIXED LANGUAGE / TYPOS
    # ------------------------------------------------------------------
    run_focus_test("כמה evants יש לפרטנר 510 בחודש לאסט?")
    run_focus_test("אני רוצה דוח על רטארגטינג אפ קמפיינס")
    run_focus_test("תראי לי קלקים של app_id 13 בשעה 0")

    # ------------------------------------------------------------------
    # GROUP 11 – EXPLANATION / METADATA QUESTIONS (NOT REALLY SQL)
    # ------------------------------------------------------------------
    run_focus_test("explain what media_source means in this table")
    run_focus_test("מה ההבדל בין is_engaged_view ל-engagement_type?")
    run_focus_test("how can we detect fraud using these fields?")

    # ------------------------------------------------------------------
    # GROUP 12 – QUESTIONS ASKING FOR SQL DIRECTLY
    # ------------------------------------------------------------------
    run_focus_test("write an SQL query that returns all partners ordered by total_events")
    run_focus_test("how do I do group by on media_source and do I need hr?")

    # ------------------------------------------------------------------
    # GROUP 13 – WELL-DEFINED, ALREADY FOCUSED (SHOULD END LOOP)
    # ------------------------------------------------------------------
    run_focus_test(
        "show me all the clicks for app id 20 on october 2025"
    )
    run_focus_test(
        "how many total_events did app_id_13 have between 2025-10-01 and 2025-10-07 for media_source_311?"
    )
    run_focus_test(
        "list all site_id for partner_507 at hour 0 on 2025-10-24"
    )
    run_focus_test(
        "show me how many events each media_source has for app_id_2 on 2025-10-24"
    )
    run_focus_test(
        "how many events with is_retargeting=true and is_engaged_view=false did app_id_450 have in the last week?"
    )

    # ------------------------------------------------------------------
    # GROUP 14 – CASES WITH PRE-FILLED refined_question (SIMULATING LOOP)
    # ------------------------------------------------------------------
    run_focus_test(
        original_question="show me clicks",
        refined_question="show me clicks for app_id_13 in october 2025",
    )
    run_focus_test(
        original_question="אני רוצה לראות פעילות חשודה",
        refined_question="show suspicious spikes in total_events per site_id for app_id_13 in the last 7 days",
    )

    print("\nALL FOCUS AGENT TESTS COMPLETED.")
