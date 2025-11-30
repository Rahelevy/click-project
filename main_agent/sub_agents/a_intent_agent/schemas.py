from pydantic import BaseModel, Field
from typing import Optional, List


class UserQuestion(BaseModel):
    question: str


class AgentAOutput(BaseModel):
    # Est-ce que la question est valide pour générer du SQL ?
    valid: bool = False

    # Dernière version de la question (éventuellement raffinée plus tard)
    question: str

    # SQL généré (seulement si valid == True)
    sql: Optional[str] = None

    # Explication pourquoi ce n'est pas valide (si valid == False)
    reason: Optional[str] = None

    # 👉 Nouveau : est-ce qu'on a besoin d'une réponse utilisateur ?
    awaiting_user_input: bool = False

    # 👉 Nouveau : quels champs manquent (date, app_id, metric, etc.)
    missing_fields: List[str] = Field(default_factory=list)

    # 👉 Nouveau : question à poser à l'utilisateur
    question_to_user: Optional[str] = None
