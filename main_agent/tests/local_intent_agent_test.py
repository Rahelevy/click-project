#$env:GOOGLE_API_KEY="AIzaSyBCCqq1cfwn0jUZ8RVPVEWV9AfcGSi0gLA"
import os
from main_agent.sub_agents.a_intent_agent import IntentAgent

# IMPORTANT:
# Make sure your .env contains GOOGLE_API_KEY
# or export it before running:
#   export GOOGLE_API_KEY="your-key"

# Simple fake state (matches what your agent expects)
class FakePart:
    def __init__(self, text):
        self.text = text

class FakeUserContent:
    def __init__(self, text):
        self.parts = [FakePart(text)]

class FakeState:
    def __init__(self, text):
        self.user_content = FakeUserContent(text)

# ---------------------------
# MAIN INTERACTIVE TEST
# ---------------------------

if __name__ == "__main__":
    print("\n=== IntentAgent Local Test ===")
    print("Type a question (or 'exit' to quit)\n")

    agent = IntentAgent()

    while True:
        question = input("User: ")
        if question.lower() in ("exit", "quit"):
            break

        state = FakeState(question)
        result = agent.run(state)

        print("\n--- Agent Output ---")
        print(result)
        print("\n--------------------\n")
