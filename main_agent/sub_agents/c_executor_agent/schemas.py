from pydantic import BaseModel
from typing import Any, Optional, List, Dict

class AgentCInput(BaseModel):
    user_question: str
    sql: str

class AgentCOutput(BaseModel):
    user_question: str
    db_result: List[Dict[str, Any]]
