from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class IntentType(str, Enum):
    RECOMMENDATION = "recommendation"
    COMPARISON     = "comparison"
    REVIEW         = "review"
    POLICY         = "policy"
    PRICE          = "price"
    GENERAL        = "general"

class ChatRequest(BaseModel):
    message:     str = Field(..., min_length=1, max_length=1000)
    session_id:  Optional[str] = None
    max_results: int = Field(default=5, ge=1, le=20)

class ChatResponse(BaseModel):
    session_id: str
    message:    str
    intent:     IntentType
    confidence: float
    entities:   dict
    agent_used: str
    response:   dict
    success:    bool
    error:      Optional[str] = None
