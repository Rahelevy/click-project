from pydantic import BaseModel
from typing import Optional


class UserQuestion(BaseModel):
    question: str


class AgentAOutput(BaseModel):
    valid: bool
    sql: Optional[str] = None
    needs_focus: Optional[bool] = None
    reason: Optional[str] = None
