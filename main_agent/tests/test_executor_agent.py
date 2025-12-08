from main_agent.sub_agents.c_executor_agent.agent import ExecutorAgent

# Create agent instance
agent = ExecutorAgent()

print("\n--- EXECUTOR AGENT TEST START ---")

# -------------------------------------------------------
# REAL QUERY TEST (safe query)
# -------------------------------------------------------
state_success = {
    "user_question": "test",
    "sql": "SELECT * FROM practicode-2025.clicks_data_prac.encoded_clicks WHERE app_id= 'app_id_20' limit 10 "
}

result_success = agent.run(state_success)
print("\n>>> SUCCESS CASE RESULT:")
print(result_success)
print(result_success["state"])


# -------------------------------------------------------
# SQL VALIDATION TEST
# -------------------------------------------------------
state_invalid_sql = {
    "user_question": "delete rows",
    "sql": "DELETE FROM my_table"
}

result_invalid = agent.run(state_invalid_sql)
print("\n>>> INVALID SQL RESULT:")
print(result_invalid)
print(result_invalid["state"])


# -------------------------------------------------------
# BROKEN SQL SYNTAX TEST
# -------------------------------------------------------
state_bad_sql = {
    "user_question": "bad sql",
    "sql": "SELECTE * FRO table"
}

result_bad = agent.run(state_bad_sql)
print("\n>>> BAD SQL RESULT:")
print(result_bad)
print(result_bad["state"])

print("\n--- EXECUTOR AGENT TEST END ---\n")
