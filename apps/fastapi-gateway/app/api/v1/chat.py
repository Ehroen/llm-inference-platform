from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # Mock LLM response (baseline)
    return ChatResponse(
        response=f"Mock response to: {req.message}"
    )
