# from main_agent.agent import root_agent  # תעדכני נתיב אם צריך

# MAX_USER_REFINEMENTS = 5

# state = {
#     "waiting_for_clarification": False,
#     "original_question": None,
#     "refinement_count": 0,
# }

# def handle_user(message: str):
#     if state["waiting_for_clarification"]:
#         combined_question = state["original_question"] + " " + message
#         state["waiting_for_clarification"] = False
#         state["original_question"] = None
#         return root_agent.run({"question": combined_question})

#     result = root_agent.run({"question": message})

#     if isinstance(result, dict) and result.get("clarification_question"):
#         state["refinement_count"] += 1

#         if state["refinement_count"] > MAX_USER_REFINEMENTS:
#             state["waiting_for_clarification"] = False
#             state["original_question"] = None
#             return {
#                 "error": (
#                     f"Sorry, I still don't have enough info after {MAX_USER_REFINEMENTS} refinements. "
#                     "Please rephrase your question more clearly."
#                 )
#             }

#         state["waiting_for_clarification"] = True
#         state["original_question"] = message
#         return {"ask_user": result["clarification_question"]}

#     if isinstance(result, dict) and result.get("valid") is True:
#         state["refinement_count"] = 0

#     return result


# if __name__ == "__main__":
#     print("Ask me about clicks. Type 'exit' to quit.")
#     while True:
#         user_msg = input("You: ").strip()
#         if user_msg.lower() == "exit":
#             break

#         out = handle_user(user_msg)

#         if isinstance(out, dict) and out.get("ask_user"):
#             print("Assistant:", out["ask_user"])
#         elif isinstance(out, dict) and out.get("error"):
#             print("Assistant:", out["error"])
#         else:
#             print("Assistant:", out)

from main_agent.agent import root_agent

MAX_USER_REFINEMENTS = 5

state = {
    "waiting": False,
    "original": None,
    "count": 0,
}

def handle_user(msg: str):
    # אם זו תשובת מיקוד
    if state["waiting"]:
        combined = state["original"] + " " + msg
        state["waiting"] = False
        state["original"] = None
        return root_agent.run({"question": combined})

    # טורן רגיל
    res = root_agent.run({"question": msg})

    # אם B ביקש מיקוד
    if isinstance(res, dict) and res.get("clarification_question"):
        state["count"] += 1
        if state["count"] > MAX_USER_REFINEMENTS:
            return {"error": "Too many refinements (5). Please rephrase."}

        state["waiting"] = True
        state["original"] = msg
        return {"ask_user": res["clarification_question"]}

    # אם valid – מאפסים מונה
    if isinstance(res, dict) and res.get("valid") is True:
        state["count"] = 0

    return res


if __name__ == "__main__":
    while True:
        u = input("You: ").strip()
        if u == "exit":
            break
        out = handle_user(u)
        if out.get("ask_user"):
            print("Assistant:", out["ask_user"])
        else:
            print("Assistant:", out)
