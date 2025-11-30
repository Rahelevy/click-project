# from main_agent.agent import root_agent

# MAX_USER_REFINEMENTS = 5

# state = {
#     "waiting": False,
#     "original": None,
#     "count": 0,
# }

# def handle_user(msg: str):
#     # אם זו תשובת מיקוד
#     if state["waiting"]:
#         combined = state["original"] + " " + msg
#         state["waiting"] = False
#         state["original"] = None
#         return root_agent.run({"question": combined})

#     # טורן רגיל
#     res = root_agent.run({"question": msg})

#     # אם B ביקש מיקוד
#     if isinstance(res, dict) and res.get("clarification_question"):
#         state["count"] += 1
#         if state["count"] > MAX_USER_REFINEMENTS:
#             return {"error": "Too many refinements (5). Please rephrase."}

#         state["waiting"] = True
#         state["original"] = msg
#         return {"ask_user": res["clarification_question"]}

#     # אם valid – מאפסים מונה
#     if isinstance(res, dict) and res.get("valid") is True:
#         state["count"] = 0

#     return res


# if __name__ == "__main__":
#     while True:
#         u = input("You: ").strip()
#         if u == "exit":
#             break
#         out = handle_user(u)
#         if out.get("ask_user"):
#             print("Assistant:", out["ask_user"])
#         else:
#             print("Assistant:", out)
