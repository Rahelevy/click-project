from pydantic import BaseModel
from typing import Literal


class ExecutorResult(BaseModel):
    status: Literal["success", "error"]
    description: str              # הסבר טכני / תוצאה גולמית מה-Executor


class ExplanationInput(BaseModel):
    user_question: str            # השאלה המקורית של המשתמש
    incoming: ExecutorResult      # בדיוק מה שמגיע מסוכן C


class ExplanationOutput(BaseModel):
    status: Literal["success", "error"]
    description: str              # נוסח ידידותי למשתמש
