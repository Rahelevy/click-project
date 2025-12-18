from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any


class ExecutorResult(BaseModel):
    status: Literal["success", "error"]
    description: str              # הסבר טכני / תוצאה גולמית מה-Executor


class ExplanationInput(BaseModel):
    user_question: str            # השאלה המקורית של המשתמש
    incoming: ExecutorResult      # בדיוק מה שמגיע מסוכן C
    db_result: Optional[list] = None  # הנתונים בפועל מה-DB


class ExplanationOutput(BaseModel):
    status: Literal["success", "error"]
    description: str              # נוסח ידידותי למשתמש
    render_type: Optional[Literal["text", "table", "chart"]] = None
    table_markdown: Optional[str] = None
    chart_image: Optional[str] = None  # PNG as markdown data URI
    chart_options: Optional[Dict[str, Any]] = None  # ECharts configuration JSON
