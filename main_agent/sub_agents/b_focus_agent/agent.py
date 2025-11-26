from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from .schemas import AgentBInput, AgentBOutput
from .fields_catalog import FILTER_FIELDS
from .focus_utils import detect_missing_fields

focus_agent = Agent(
    name="b_focus_agent",
    model="gemini-2.0-flash",


    description="Focus Agent – helps user add missing filter fields to make question SQL-valid.",
    instruction="""
You are Agent B – Focus Agent.

You receive:
original_question
reason why Agent A couldn't convert it
attempt number
>>>>>>> 034be24 (my changes to focus agent)

Your job:
1. Detect which filter fields are missing (at least one filter is required).
2. Ask ONE short clarification question that gives the user 2–4 relevant field options to fill.
3. User may answer with values for one or more fields.
4. Rewrite the question into a refined version including the new field values.
5. Return refined_question to Agent A.

Rules:
Do NOT generate SQL.
Do NOT execute SQL.
Do NOT explain SQL.
If attempt == 3 and still missing → return failed=true with a polite error message.
Keep clarification questions super short and clear.
Return ONLY valid JSON matching AgentBOutput schema.
"""
)

focus_tool = AgentTool(focus_agent)


def build_clarification_question(missing_fields, lang="he"):
    # ניקח עד 4 אופציות שהכי הגיוניות למשתמש
    options = missing_fields[:4]

    if lang == "he":
        opts_text = "\n".join([f"- {FILTER_FIELDS[f]['label']}" for f in options])
        return (
            "כדי שאוכל לעזור, חסר לי לפחות פילטר אחד. "
            "איזה מהשדות הבאים תרצה/י להוסיף?\n"
            f"{opts_text}\n"
            "אפשר לבחור אחד או יותר ולכתוב ערך."
        )
    else:
        opts_text = "\n".join([f"- {FILTER_FIELDS[f]['label']}" for f in options])
        return (
            "To help you, I need at least one filter. "
            "Which of the following fields would you like to add?\n"
            f"{opts_text}\n"
            "You can choose one or more and provide a value."
        )


def focus_logic(input_data: AgentBInput, user_answer: str = "", lang: str = "he") -> AgentBOutput:
    missing = detect_missing_fields(input_data.original_question)

    # אם חסר כלום – אין מה למקד
    if not missing:
        return AgentBOutput(
            refined_question=input_data.original_question,
            attempt=input_data.attempt,
            missing_fields=[]
        )

    # אם זה ניסיון שלישי
    if input_data.attempt >= 3:
        return AgentBOutput(
            failed=True,
            attempt=input_data.attempt,
            missing_fields=missing,
            error_message="לא הצלחנו למקד את השאלה אחרי 3 ניסיונות. נסה/י לשאול מחדש בצורה יותר ממוקדת."
            if lang=="he"
            else "Unable to refine the question after 3 attempts. Please ask again more specifically."
        )

    # אם אין תשובת משתמש עדיין → נחזיר את שאלת ההבהרה
    if not user_answer.strip():
        clarification = build_clarification_question(missing, lang)
        return AgentBOutput(
            clarification_question=clarification,
            missing_fields=missing,
            attempt=input_data.attempt
        )

    # יש תשובת משתמש → נייצר שאלה חדשה
    refined = f"{input_data.original_question}. Additional details: {user_answer}"
    return AgentBOutput(
        refined_question=refined,
        missing_fields=missing,
        attempt=input_data.attempt + 1
    )