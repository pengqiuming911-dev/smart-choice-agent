"""Pydantic models for API request/response"""
from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    user_open_id: str = Field(..., description="User's open ID in Feishu")
    user_name: str = Field(default="Unknown", description="User display name")
    question: str = Field(..., description="User question", max_length=2000)
    session_id: Optional[str] = Field(None, description="Session ID for multi-turn conversation")
    doc_ids: Optional[List[str]] = Field(None, description="Specific document IDs to search")
    top_k: Optional[int] = Field(5, description="Number of chunks to retrieve", ge=1, le=20)


class SearchRequest(BaseModel):
    """Request model for search-only endpoint"""
    query: str = Field(..., description="Search query", max_length=500)
    user_open_id: Optional[str] = Field(None, description="User ID for permission filtering")
    doc_ids: Optional[List[str]] = Field(None, description="Specific document IDs to search")
    top_k: Optional[int] = Field(5, description="Number of chunks to retrieve", ge=1, le=20)


class Citation(BaseModel):
    """Citation for a source document"""
    title: str
    document_id: str
    score: float = Field(0.0, description="Relevance score")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    session_id: str = Field(..., description="Session ID")
    answer: str = Field(..., description="Generated answer")
    citations: List[Citation] = Field(default_factory=list, description="Source citations")
    blocked: bool = Field(False, description="Whether the response was blocked by compliance")
    latency_ms: int = Field(..., description="Response time in milliseconds")


class SearchResponse(BaseModel):
    """Response model for search endpoint"""
    chunks: List[dict] = Field(..., description="Retrieved document chunks")
    total: int = Field(..., description="Total number of chunks retrieved")


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    timestamp: float
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    """Response model for errors"""
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
