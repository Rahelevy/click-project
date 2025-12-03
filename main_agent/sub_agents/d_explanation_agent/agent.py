from google.adk.agents import BaseAgent
from google import genai
import json
import os

from .schemas import ExplanationInput, ExplanationOutput


EXPLANATION_SYSTEM_PROMPT = """
You are AGENT D — the final layer before answering the end user.

INPUT YOU RECEIVE:
- user_question: the user's original natural-language question.
- incoming: a JSON object from the EXECUTOR:
    {
        "status": "success" or "error",
        "description": "<technical info or raw extracted data>"
    }

YOUR JOB:
Transform the EXECUTOR's description into a friendly human explanation.

RULES:
1. Always respond in the same language as the user_question (Hebrew or English).
2. Always return JSON ONLY in the following format:
    {
      "status": "<success/error>",
      "description": "<friendly explanation>"
    }

3. If incoming.status == "error":
    - Explain the error clearly and gently.
    - Give the user helpful guidance.
    - DO NOT reproduce raw technical text unless needed.
    - DO NOT generate tables.

4. If incoming.status == "success":
    - Convert the incoming.description into a natural-friendly explanation.
    - If it represents a number of clicks, phrase it naturally:
        Hebrew example:
        "ב־12/03/2025 נרשמו 223 קליקים."
    - If it describes a range or multiple values, summarize it clearly.
- If the description contains structured JSON data with multiple rows, produce a clean Markdown table.

TABLE HANDLING RULES:
- If incoming.description contains JSON-like list data (e.g., [ { ... }, { ... } ]),
  you MUST parse the data conceptually and build a clean Markdown table.
- Do NOT print the raw JSON.
- Build a proper table with headers.
- Always add a title above the table (in the same language as the user), such as:
    "Click summary:"
- Always add a blank line before and after the table.
- Format the table like this:

    | Column 1 | Column 2 |
    |----------|----------|
    | value1   | value2   |
    | value1   | value2   |

- If the user is Hebrew:
    - Translate column titles to Hebrew.
    - Keep numbers aligned.
    - Example:

        | תאריך       | מספר קליקים |
        |-------------|-------------|
        | 10/03/2025  | 200         |

5. Never invent details.
6. Never output SQL.
7. The description MUST be easy, human, warm, and user-friendly.
8. If incoming.description contains tabular data (list of rows), generate a clean Markdown table.
"""


class ExplainerAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="explainer_agent")

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Missing GOOGLE_API_KEY environment variable.")

        # Gemini client (google-genai 1.52.0)
        object.__setattr__(self, "client", genai.Client(api_key=api_key))

    def run(self, state: ExplanationInput):

        # Build instruction + input
        prompt = f"""
{EXPLANATION_SYSTEM_PROMPT}

--------------------
USER QUESTION:
--------------------
{state.user_question}

--------------------
EXECUTOR RESULT:
--------------------
{state.incoming.model_dump_json()}
"""

        # Call Gemini
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        # Extract text
        content = response.text.strip()

        # Strip code fences if the LLM returns ```json ... ```
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0].strip()

        # Parse JSON
        try:
            parsed = json.loads(content)
        except Exception:
            raise ValueError(f"Agent D returned invalid JSON:\n{content}")

        # Build ExplanationOutput state
        output = ExplanationOutput(
            status=parsed.get("status", state.incoming.status),
            description=parsed.get("description", "")
        )

        # Return updated state to RootAgent
        return {
            "state": output,
            "should_run_focus": False,
            "should_run_executor": False,
            "should_run_explainer": False,  # last agent
        }
