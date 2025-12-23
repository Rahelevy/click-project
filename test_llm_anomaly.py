"""Test to see what LLM actually returns for paraphrased anomaly queries"""
from main_agent.sub_agents.a_intent_agent.agent import IntentAgent
import json

def test_llm_response():
    """Test what LLM returns for non-keyword anomaly query"""
    intent = IntentAgent()
    
    # Query that should trigger anomaly but has NO keywords
    query = "which media sources are behaving strangely"
    
    print(f"\n=== Testing query: '{query}' ===\n")
    
    # Run and inspect
    result = intent.run({"question": query})
    state = result.get("state", {})
    
    print("Full state returned:")
    print(json.dumps(state, indent=2))
    print(f"\nquery_type: {state.get('query_type')}")
    print(f"valid: {state.get('valid')}")
    print(f"sql: {state.get('sql')}")
    
    # Another test - very paraphrased
    query2 = "find patterns that seem off"
    print(f"\n\n=== Testing query: '{query2}' ===\n")
    
    result2 = intent.run({"question": query2})
    state2 = result2.get("state", {})
    
    print("Full state returned:")
    print(json.dumps(state2, indent=2))
    print(f"\nquery_type: {state2.get('query_type')}")
    print(f"valid: {state2.get('valid')}")

if __name__ == "__main__":
    test_llm_response()
