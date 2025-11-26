from pydantic import BaseModel
from typing import List, Optional

class AgentBInput(BaseModel):
    original_question: str
    reason: str
    attempt: int = 1  # כמה פעמים כבר ניסינו למקד

class AgentBOutput(BaseModel):
    refined_question: Optional[str] = None
    clarification_question: Optional[str] = None
    missing_fields: List[str] = []
    attempt: int = 1
    failed: bool = False
    error_message: Optional[str] = None