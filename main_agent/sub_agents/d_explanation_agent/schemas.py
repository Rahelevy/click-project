from pydantic import BaseModel
from typing import Literal, Any, Optional


class ExecutorResult(BaseModel):
    status: Literal["success", "error"]
    description: str              # הסבר טכני / תוצאה גולמית מה-Executor


class ExplanationInput(BaseModel):
    user_question: str            # השאלה המקורית של המשתמש
    incoming: ExecutorResult      # בדיוק מה שמגיע מסוכן C
    db_result: Optional[Any] = None  # הנתונים בפועל (רשימת שורות)
    sql: Optional[str] = None     # SQL query for debugging


class ExplanationOutput(BaseModel):
    status: Literal["success", "error"]
    description: str              # נוסח ידידותי למשתמש
