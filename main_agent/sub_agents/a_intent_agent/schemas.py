from pydantic import BaseModel
from typing import Optional

class UserQuestion(BaseModel):
    question: str

class AgentAOutput(BaseModel):
    valid: bool
    needs_focus: bool = False
    question: str
    sql: Optional[str] = None
    reason: Optional[str] = None
