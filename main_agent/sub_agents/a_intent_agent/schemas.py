from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class UserQuestion(BaseModel):
    question: str


class AgentAOutput(BaseModel):
    valid: bool = False
    question: str
    query_type: Optional[Literal["sql", "anomaly"]] = "sql"  # Route queries by type
    sql: Optional[str] = None
    reason: Optional[str] = None
    awaiting_user_input: bool = False
    missing_fields: List[str] = Field(default_factory=list)
