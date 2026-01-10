"""
Paper API Schemas
Response models for paper-related endpoints.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AuthorSchema(BaseModel):
    """Author information."""
    name: str
    author_id: Optional[str] = None


class PaperSummary(BaseModel):
    """Brief paper information for lists."""
    arxiv_id: str = Field(..., description="arXiv ID (e.g., 2401.12345)")
    title: str
    abstract: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    published_date: Optional[str] = None
    citation_count: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "arxiv_id": "2401.12345",
                "title": "Quantum Error Correction via Surface Codes",
                "abstract": "We present a novel approach to quantum error correction...",
                "authors": ["Alice Smith", "Bob Jones"],
                "categories": ["quant-ph", "math.QA"],
                "published_date": "2024-01-15",
                "citation_count": 42,
            }
        }


class PaperDetail(BaseModel):
    """Full paper information with relationships."""
    arxiv_id: str
    title: str
    abstract: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    published_date: Optional[str] = None
    
    # Semantic Scholar data
    s2_id: Optional[str] = None
    citation_count: Optional[int] = None
    reference_count: Optional[int] = None
    influential_citation_count: Optional[int] = None
    tl_dr: Optional[str] = Field(None, description="AI-generated TL;DR from Semantic Scholar")
    
    # AI-generated content
    summary: Optional[str] = Field(None, description="LLM-generated summary")
    
    # Relationships
    citations: list[PaperSummary] = Field(
        default_factory=list,
        description="Papers that cite this paper",
    )
    references: list[PaperSummary] = Field(
        default_factory=list,
        description="Papers cited by this paper",
    )
    
    # Graph metrics
    pagerank: Optional[float] = None
    betweenness: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "arxiv_id": "2401.12345",
                "title": "Quantum Error Correction via Surface Codes",
                "abstract": "We present a novel approach...",
                "authors": ["Alice Smith", "Bob Jones"],
                "categories": ["quant-ph", "math.QA"],
                "published_date": "2024-01-15",
                "s2_id": "abc123",
                "citation_count": 42,
                "reference_count": 28,
                "tl_dr": "Novel quantum error correction using surface codes",
                "summary": "This paper introduces...",
                "pagerank": 0.0023,
            }
        }


class PaperListResponse(BaseModel):
    """Paginated list of papers."""
    papers: list[PaperSummary]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "papers": [],
                "total": 150,
                "page": 1,
                "page_size": 20,
                "has_next": True,
                "has_prev": False,
            }
        }


class PaperBatchRequest(BaseModel):
    """Request to fetch multiple papers."""
    arxiv_ids: list[str] = Field(..., min_length=1, max_length=50)
    
    class Config:
        json_schema_extra = {
            "example": {
                "arxiv_ids": ["2401.12345", "2402.13579", "2403.14680"]
            }
        }


class PaperBatchResponse(BaseModel):
    """Response with multiple papers."""
    papers: list[PaperSummary]
    found: int
    not_found: list[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "papers": [],
                "found": 2,
                "not_found": ["2404.99999"],
            }
        }