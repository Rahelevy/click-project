from main_agent.sub_agents.c_executor_agent.agent import ExecutorAgent

agent = ExecutorAgent()

state = {
    "user_question": "show me sample rows",
    "sql": """
        SELECT *
        FROM `practicode-2025.clicks_data_prac.encoded_clicks_partitioned`
        WHERE app_id = 'app_id_20'
        LIMIT 10
    """
}

result = agent.run(state)

print("\n=== RAW EXECUTOR RESULT ===")
print(result)
print("\n=== ROWS ===")
print(result["state"].db_result)
