# b_focus_agent/agent.py
from google.adk.agents import Agent
from .schemas import AgentBInput, AgentBOutput
from .fields_catalog import FILTER_FIELDS
from .focus_utils import detect_missing_fields
from .tools import exit_loop

focus_agent = Agent(
    name="b_focus_agent",
    model="gemini-2.5-flash",
    description="Focus Agent – helps user add missing filter fields to make question SQL-valid.",
 instruction="""
You are Agent B – Focus Agent.

You receive JSON with:
- original_question
- reason (why Agent A couldn't convert it)
- attempt (attempt number)

FIRST STEP:
Run detect_missing_fields(original_question).

IF missing_fields is empty:
Return ONLY:
{
  "refined_question": "<original_question>",
  "failed": false,
  "attempt": <attempt>,
  "missing_fields": []
}
and STOP.

Your job:
1. Detect which filter fields are missing (at least one filter is required).
2. Ask ONE short clarification question that gives the user 2–4 relevant field options to fill.
3. If user already provided values, rewrite the question into a refined version including them.
4. Return ONLY valid JSON matching AgentBOutput schema.

Rules:
- Do NOT generate SQL.
- Do NOT execute SQL.
- Do NOT explain SQL.
- If attempt >= 3 and still missing → return failed=true with a polite error_message.
- Keep clarification questions super short and clear.

If you return "clarification_question" to the user,
you MUST call exit_loop() immediately after.


""",
    input_schema=AgentBInput,
    output_schema=AgentBOutput,
    tools=[exit_loop],
)
