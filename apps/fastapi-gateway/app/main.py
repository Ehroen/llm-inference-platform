from fastapi import FastAPI
from app.api.v1.chat import router as chat_router

app = FastAPI(
    title="LLM Gateway",
    version="0.1.0",
    description="FastAPI gateway for LLM inference"
)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(chat_router, prefix="/v1")
