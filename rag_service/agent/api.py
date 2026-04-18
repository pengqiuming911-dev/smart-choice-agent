"""FastAPI server for RAG Agent - Step 7 implementation"""
import os
import sys
import uuid
import time
import logging
from contextlib import asynccontextmanager
from typing import Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from rag_service.agent.models import (
    ChatRequest, ChatResponse, SearchRequest, SearchResponse,
    HealthResponse, ErrorResponse, Citation
)
from rag_service.agent.rag_agent import RAGAgent
from rag_service.models.db import get_stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("rag_api")

# Global agent instance
_agent = None


def get_agent() -> RAGAgent:
    global _agent
    if _agent is None:
        _agent = RAGAgent()
    return _agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("RAG API starting up...")
    yield
    logger.info("RAG API shutting down...")


app = FastAPI(
    title="PE Knowledge Base RAG API",
    description="私募基金知识库问答 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Inject X-Request-ID header for request tracing"""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests with latency and status"""
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(
        f"Request started | {request_id} | {request.method} {request.url.path}"
    )

    try:
        response = await call_next(request)
        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Request completed | {request_id} | {request.method} {request.url.path} | "
            f"status={response.status_code} | latency={latency_ms}ms"
        )

        return response
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            f"Request failed | {request_id} | {request.method} {request.url.path} | "
            f"error={type(e).__name__} | latency={latency_ms}ms"
        )
        raise


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Unhandled exception | {request_id} | {type(exc).__name__}: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") else None,
            "request_id": request_id,
        },
    )


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    """
    Chat endpoint - ask a question using RAG.

    Returns a generated answer with source citations.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(f"Chat request | {request_id} | user={req.user_open_id} | question_len={len(req.question)}")

    try:
        agent = get_agent()

        result = agent.answer(
            question=req.question,
            user_open_id=req.user_open_id,
            doc_ids=req.doc_ids,
            session_id=req.session_id or str(uuid.uuid4()),
            user_name=req.user_name,
        )

        # Build response
        session_id = req.session_id or result.get("session_id", str(uuid.uuid4()))
        citations = [
            Citation(
                title=c.get("title", "Unknown"),
                document_id=c.get("document_id", ""),
                score=c.get("score", 0.0),
            )
            for c in result.get("citations", [])
        ]

        # Check if blocked (compliance)
        blocked = result.get("blocked", False)

        return ChatResponse(
            session_id=session_id,
            answer=result["answer"],
            citations=citations,
            blocked=blocked,
            latency_ms=result.get("latency_ms", 0),
        )

    except Exception as e:
        logger.error(f"Chat error | {request_id} | {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/search", response_model=SearchResponse)
async def search(req: SearchRequest, request: Request):
    """
    Search endpoint - retrieve relevant chunks without generating answer.

    Useful for debugging retrieval quality.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(f"Search request | {request_id} | query_len={len(req.query)}")

    try:
        agent = get_agent()

        chunks = agent.retrieve(
            query=req.query,
            doc_ids=req.doc_ids,
        )

        return SearchResponse(
            chunks=[
                {
                    "content": c.content,
                    "title": c.title,
                    "document_id": c.document_id,
                    "score": c.score,
                    "path": c.path,
                }
                for c in chunks[: req.top_k]
            ],
            total=len(chunks),
        )

    except Exception as e:
        logger.error(f"Search error | {request_id} | {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        timestamp=time.time(),
    )


@app.get("/api/v1/stats")
async def stats():
    """Get knowledge base statistics"""
    try:
        return get_stats()
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("RAG_API_PORT", "8080"))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        timeout_keep_alive=60,  # 60 second timeout
        log_level="info",
    )
