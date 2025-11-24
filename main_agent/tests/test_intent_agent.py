import asyncio
from main_agent.agent import root_agent

async def test_root():
    print("\n=== TEST ROOT AGENT (simple) ===\n")

    # La méthode OFFICIELLE ADK 1.19
    result = await root_agent.run_with_user_prompt(
        "count events for app app_id_20"
    )

    print("\n=== RESULT ===")
    print(result)

if __name__ == "__main__":
    asyncio.run(test_root())
