# test_root_agent.py
import asyncio
from main_agent.agent import root_agent

# --------- Fake ADK-like objects ---------
class FakePart:
    def __init__(self, text):
        self.text = text

class FakeContent:
    def __init__(self, text):
        self.parts = [FakePart(text)]

class FakeSession:
    def __init__(self):
        self.state = {}

class FakeCtx:
    def __init__(self, text, session):
        self.user_content = FakeContent(text)
        self.session = session

# --------- Test ---------
async def test_root():
    session = FakeSession()
    ctx = FakeCtx("תן לי את כל הדאטה", session)

    events = []
    async for ev in root_agent._run_async_impl(ctx):
        events.append(ev)

    # נדפיס את התוצאה
    print("\n--- Root output ---")
    for ev in events:
        print("answer:", ev.content.parts[0].text)
        print("state_delta:", ev.actions.state_delta)

if __name__ == "__main__":
    asyncio.run(test_root())
