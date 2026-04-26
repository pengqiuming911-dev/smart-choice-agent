"""Pydantic models for wiki_service API"""
from pydantic import BaseModel
from typing import Optional


class QueryRequest(BaseModel):
    question: str
    user_id: Optional[str] = None


class WikiPage(BaseModel):
    title: str
    path: str


class RawSource(BaseModel):
    title: str
    path: str


class QueryResponse(BaseModel):
    answer: str
    wiki_pages: list[WikiPage]
    raw_sources: list[RawSource]
    confidence: str


class IngestRequest(BaseModel):
    doc_token: Optional[str] = None
    file_path: Optional[str] = None


class IngestResponse(BaseModel):
    success: bool
    message: str
    pages_created: int = 0
    pages_updated: int = 0


class LintReport(BaseModel):
    orphaned_pages: list[str]
    broken_links: list[str]
    contradictions: list[str]
    stale_pages: list[str]
    suggestions: list[str]
