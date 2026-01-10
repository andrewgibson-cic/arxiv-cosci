"""
Search API Schemas
Request and response models for search endpoints.
"""
from typing import Optional, Literal

from pydantic import BaseModel, Field

from apps.api.schemas.paper import PaperSummary


class SearchRequest(BaseModel):
    """Search request parameters."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(10, ge=1, le=50, description="Maximum results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "quantum error correction",
                "limit": 10,
            }
        }


class SearchResult(BaseModel):
    """Single search result with relevance score."""
    paper: PaperSummary
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    
    class Config:
        json_schema_extra = {
            "example": {
                "paper": {
                    "arxiv_id": "2401.12345",
                    "title": "Quantum Error Correction",
                    "abstract": "We present...",
                    "authors": ["Alice Smith"],
                    "categories": ["quant-ph"],
                    "published_date": "2024-01-15",
                },
                "score": 0.85,
            }
        }


class SearchResponse(BaseModel):
    """Search results response."""
    results: list[SearchResult]
    query: str
    total: int
    search_type: Literal["semantic", "hybrid"]
    
    class Config:
        json_schema_extra = {
            "example": {
                "results": [],
                "query": "quantum error correction",
                "total": 42,
                "search_type": "semantic",
            }
        }


class SimilarPapersResponse(BaseModel):
    """Response for similar papers query."""
    arxiv_id: str
    similar_papers: list[SearchResult]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "arxiv_id": "2401.12345",
                "similar_papers": [],
                "total": 15,
            }
        }