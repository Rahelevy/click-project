from pydantic import BaseModel
from typing import Literal, Any


class IncomingResult(BaseModel):
    status: Literal["success", "error"]
    description: str


class AgentCOutput(BaseModel):
    user_question: str
    incoming: IncomingResult
    db_result: Any   # list of rows OR {"total": number}
