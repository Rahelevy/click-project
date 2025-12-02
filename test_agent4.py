import asyncio
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

from main_agent.sub_agents.d_explanation_agent.agent import explainer_agent
from main_agent.sub_agents.d_explanation_agent.schemas import ExecutorResult


# ----------------------------------------------------
# 1. LOAD .env AND CONFIGURE API KEY
# ----------------------------------------------------
load_dotenv("main_agent/.env")

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise Exception("GOOGLE_API_KEY is missing from main_agent/.env!")

genai.configure(api_key=api_key)


# ----------------------------------------------------
# 2. SIMPLE FUNCTION THAT CALLS AGENT D LOGIC
# ----------------------------------------------------
def run_explainer(user_question: str, incoming: ExecutorResult) -> str:
    """
    Calls Gemini directly using the same system instruction as Agent D.
    Returns the raw text from the model (which should be a JSON with
    { "status": "...", "description": "..." } ).
    """

    # זה בדיוק ה־input שסוכן ד אמור לקבל
    payload = {
        "user_question": user_question,
        "incoming": incoming.model_dump(),
    }

    # בונים prompt אחד ארוך – בלי roles, בלי מבנה מיוחד
    prompt = (
        explainer_agent.instruction
        + "\n\n--- JSON INPUT FROM EXECUTOR ---\n"
        + json.dumps(payload, ensure_ascii=False)
        + "\n\nRemember: respond ONLY with JSON of the form:\n"
        + '{ "status": "<success or error>", "description": "<friendly explanation>" }'
    )

    # משתמשים בשם המודל מתוך הסוכן (gemini-2.5-flash)
    model = genai.GenerativeModel(explainer_agent.model)

    response = model.generate_content(prompt)
    return response.text


# ----------------------------------------------------
# 3. MAIN – RUN TWO TESTS: SUCCESS + ERROR
# ----------------------------------------------------
def main():
    print("\n==============================")
    print(" SUCCESS CASE")
    print("==============================\n")

    success_input = ExecutorResult(
        status="success",
        description="On 12/03/2025 the system recorded 223 clicks."
    )

    success_result = run_explainer(
        user_question="How many clicks were on March 12th, 2025?",
        incoming=success_input,
    )

    print("Model raw output:\n")
    print(success_result)

    print("\n==============================")
    print(" ERROR CASE")
    print("==============================\n")

    error_input = ExecutorResult(
        status="error",
        description="No matching data was found in the database for the requested date."
    )

    error_result = run_explainer(
        user_question="How many clicks were on March 12th, 2025?",
        incoming=error_input,
    )

    print("Model raw output:\n")
    print(error_result)

# ==============================
# TABLE CASE
# ==============================
print("\n==============================")
print(" TABLE CASE")
print("==============================\n")

table_description = """
Here is the raw data:
[
  {"date": "2025-03-10", "clicks": 200},
  {"date": "2025-03-11", "clicks": 215},
  {"date": "2025-03-12", "clicks": 223}
]
"""

table_input = ExecutorResult(
    status="success",
    description=table_description
)

result = run_explainer(
    user_question="Give me a summary of clicks for the last 3 days.",
    incoming=table_input
)

print("Model raw output:\n")
print(result)


if __name__ == "__main__":
    main()
