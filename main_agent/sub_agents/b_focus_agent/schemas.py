from pydantic import BaseModel, Field
from typing import List, Optional


class AgentBInput(BaseModel):
    """
    Input passed into Agent B (Focus Agent).

    - original_question: the original user question text.
    - reason: short explanation from Agent A why the question was not valid.
    """
    original_question: str
    reason: str


class AgentBOutput(BaseModel):
    """
    Output from the Focus Agent.

    Behavior:
    - If more user information is required:
        awaiting_user_input = true
        question_to_user must contain exactly one clear question.
        missing_fields must describe which fields are needed.

    - If the question can be refined using existing details:
        awaiting_user_input = false
        refined_question must contain the updated question.
        missing_fields should be empty.

    Never return both refined_question and question_to_user at the same time.
    """

    # NEW — matches Agent A
    awaiting_user_input: bool = False

    # NEW — replaces clarification_question
    question_to_user: Optional[str] = None

    # When enough info → refined question
    refined_question: Optional[str] = None

    # Missing fields needed
    missing_fields: List[str] = Field(default_factory=list)

    # Error management
    failed: bool = False
    error_message: Optional[str] = None
