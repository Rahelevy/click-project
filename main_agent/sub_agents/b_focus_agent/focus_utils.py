# focus_utils.py
import re
from typing import List

# מזהים האם שדה קיים בשאלה (גם בעברית וגם באנגלית)
FIELD_PATTERNS = {
    "app_id": [r"app(?:_id)?\s+\S+", r"אפליקציה\s+\S+", r"אפליקציית\s+\S+"],
    "media_source": [r"media[_ ]source\s+\S+", r"מקור\s+מדיה\s+\S+"],
    "partner": [r"partner\s+\S+", r"שותף\s+\S+"],
    "site_id": [r"site[_ ]id\s+\S+", r"אתר\s+\S+"],
    "engagement_type": [r"engagement[_ ]type\s+\S+", r"סוג\s+מעורבות\s+\S+"],
    "hour": [r"\bat\s+\d{1,2}:\d{2}\b", r"שעה\s+\d{1,2}"],
    "date": [r"\b\d{4}-\d{2}-\d{2}\b", r"\b\d{2}/\d{2}/\d{4}\b"],
    "is_engaged_view": [r"engaged view", r"צפייה\s+מעורבת"],
    "is_retargeting": [r"retargeting", r"ריטרגטינג"]
}

def detect_present_fields(question: str) -> List[str]:
    q = question.lower()
    present = []
    for field, patterns in FIELD_PATTERNS.items():
        for p in patterns:
            if re.search(p, q):
                present.append(field)
                break
    return present

def detect_missing_fields(question: str, required_minimum: int = 1) -> List[str]:
    """
    שאלה תקינה חייבת לכלול לפחות פילטר אחד.
    מחזיר מה חסר (אם אין שום פילטר).
    """
    present = detect_present_fields(question)
    if len(present) >= required_minimum:
        return []  # הכל טוב
    # אז חסר לפחות אחד -> נחזיר רשימת אופציות
    return [f for f in FIELD_PATTERNS.keys() if f not in present]