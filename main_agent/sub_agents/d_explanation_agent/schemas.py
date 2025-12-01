from pydantic import BaseModel
from typing import Any

class ExplanationInput(BaseModel):
    user_question: str
    db_result: Any

class ExplanationOutput(BaseModel):
    answer_text: str
