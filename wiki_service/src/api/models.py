"""Pydantic models for API - matches ARCHITECTURE.md QueryResponse structure"""
from pydantic import BaseModel
from typing import Optional


class WikiPage(BaseModel):
    """A wiki page reference"""
    title: str
    path: str


class RawSource(BaseModel):
    """A raw source document reference"""
    title: str
    path: str
    type: str = "wiki"  # wiki or feishu


class QueryRequest(BaseModel):
    """Query request from user"""
    question: str
    user_id: Optional[str] = None


class QueryResponse(BaseModel):
    """
    Query response structure from ARCHITECTURE.md:

    ```json
    {
      "answer": "Q3 华东区销售目标是 2400 万...",
      "wiki_pages": [{"title": "Q3 销售目标", "url": "/wiki/entities/q3-sales-goal"}],
      "raw_sources": [{"title": "2026Q3规划.docx", "url": "feishu://docs/xxx"}],
      "confidence": "high"
    }
    ```
    """
    answer: str
    wiki_pages: list[WikiPage] = []
    raw_sources: list[RawSource] = []
    confidence: str = "medium"


class IngestRequest(BaseModel):
    """Ingest request - either doc_token (Feishu) or file_path (local)"""
    doc_token: Optional[str] = None
    file_path: Optional[str] = None


class IngestResponse(BaseModel):
    """Ingest response"""
    success: bool
    message: str
    pages_created: int = 0
    pages_updated: int = 0


class LintReport(BaseModel):
    """Lint report as defined in ARCHITECTURE.md"""
    orphaned_pages: list[str] = []
    broken_links: list[str] = []
    contradictions: list[str] = []
    stale_pages: list[str] = []
    suggestions: list[str] = []


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    wiki_repo: str
    repo_exists: bool