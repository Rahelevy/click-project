from main_agent.sub_agents.b_focus_agent.agent import FocusAgent

agent = FocusAgent()

# 1) dict כמו מה-Root
state_dict = {
    "question": "show me clicks from app 2 yesterday",
    "reason": "missing_date",
    "missing_fields": ["date"],
    "refined_question": None
}
norm = agent._normalize_state(state_dict)
print("DICT normalize:", norm)

# 2) dict חסר reason/missing_fields
state_dict2 = {"question": "show me clicks"}
norm2 = agent._normalize_state(state_dict2)
print("DICT missing fields normalize:", norm2)

# 3) string
norm3 = agent._normalize_state("just a string question")
print("STRING normalize:", norm3)
