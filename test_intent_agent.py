from main_agent.sub_agents.a_intent_agent.agent import IntentAgent

A = IntentAgent()

tests = [
    {"question": ""},  # empty
    {"question": "תן לי את כל הדאטה"},  # too broad
    {"question": "כמה קליקים היו ב app id 2 בין 10-01-2025 ל 10-03-2025?"},  # valid
]

for i, t in enumerate(tests, 1):
    out = A.run(t)
    print(f"\n--- Test {i} ---")
    print(out)
