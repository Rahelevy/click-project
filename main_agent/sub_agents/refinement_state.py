from pydantic import BaseModel
from typing import List, Optional

class RefinementState(BaseModel):
    question: str
    awaiting_user_input: bool = False
    missing_fields: List[str] = []
    question_to_user: Optional[str] = None
    refined_question: Optional[str] = None
