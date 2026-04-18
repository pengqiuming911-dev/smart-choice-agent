"""FastAPI server for RAG Agent"""
import os
import sys
import uuid
from typing import Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_service.agent.rag_agent import RAGAgent

app = FastAPI(title="PE Knowledge Base RAG API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
_agent = None


def get_agent() -> RAGAgent:
    global _agent
    if _agent is None:
        _agent = RAGAgent()
    return _agent


class QuestionRequest(BaseModel):
    question: str
    user_open_id: Optional[str] = None
    doc_ids: Optional[List[str]] = None
    session_id: Optional[str] = None
    user_name: Optional[str] = None
    top_k: Optional[int] = 5


class QuestionResponse(BaseModel):
    answer: str
    citations: List[dict]
    latency_ms: int


@app.post("/api/question", response_model=QuestionResponse)
async def ask_question(req: QuestionRequest):
    """Ask a question using RAG"""
    agent = get_agent()

    result = agent.answer(
        question=req.question,
        user_open_id=req.user_open_id,
        doc_ids=req.doc_ids,
        session_id=req.session_id or str(uuid.uuid4()),
        user_name=req.user_name,
    )

    return QuestionResponse(
        answer=result["answer"],
        citations=result["citations"],
        latency_ms=result["latency_ms"],
    )


@app.get("/api/health")
async def health():
    """Health check"""
    return {"status": "ok"}


@app.get("/api/stats")
async def stats():
    """Get knowledge base stats"""
    from rag_service.models.db import get_stats
    return get_stats()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("RAG_API_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
