from pydantic import BaseModel, Field

class PolicyAskRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500,
        description="Policy question, e.g. 'What is the return policy for electronics?'")
    k: int = Field(default=3, ge=1, le=10, description="Number of policy chunks to retrieve")

class PolicyAskResponse(BaseModel):
    query:      str
    answer:     str
    sources:    list[str]
    confidence: str
    agent:      str
