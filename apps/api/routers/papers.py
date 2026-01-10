"""
Papers Router
Endpoints for paper CRUD operations.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j.exceptions import Neo4jError

from apps.api.dependencies import get_neo4j_client, get_settings_cached
from apps.api.config import Settings
from apps.api.schemas.paper import (
    PaperSummary,
    PaperDetail,
    PaperListResponse,
    PaperBatchRequest,
    PaperBatchResponse,
)
from packages.knowledge.neo4j_client import Neo4jClient


router = APIRouter()


def _paper_record_to_summary(record: dict) -> PaperSummary:
    """Convert Neo4j record to PaperSummary."""
    return PaperSummary(
        arxiv_id=record.get("arxiv_id", ""),
        title=record.get("title", ""),
        abstract=record.get("abstract"),
        authors=record.get("authors", []),
        categories=record.get("categories", []),
        published_date=record.get("published_date"),
        citation_count=record.get("citation_count"),
    )


def _paper_record_to_detail(record: dict) -> PaperDetail:
    """Convert Neo4j record to PaperDetail."""
    return PaperDetail(
        arxiv_id=record.get("arxiv_id", ""),
        title=record.get("title", ""),
        abstract=record.get("abstract"),
        authors=record.get("authors", []),
        categories=record.get("categories", []),
        published_date=record.get("published_date"),
        s2_id=record.get("s2_id"),
        citation_count=record.get("citation_count"),
        reference_count=record.get("reference_count"),
        influential_citation_count=record.get("influential_citation_count"),
        tl_dr=record.get("tl_dr"),
        summary=record.get("summary"),
        pagerank=record.get("pagerank"),
        betweenness=record.get("betweenness"),
    )


@router.get("/", response_model=PaperListResponse)
async def list_papers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by arXiv category"),
    neo4j: Neo4jClient = Depends(get_neo4j_client),
    settings: Settings = Depends(get_settings_cached),
) -> PaperListResponse:
    """
    List papers with pagination.
    Optionally filter by category.
    """
    try:
        # Limit page size
        page_size = min(page_size, settings.max_page_size)
        skip = (page - 1) * page_size
        
        # Build query
        if category:
            query = """
            MATCH (p:Paper)
            WHERE $category IN p.categories
            RETURN p
            ORDER BY p.published_date DESC
            SKIP $skip
            LIMIT $limit
            """
            count_query = """
            MATCH (p:Paper)
            WHERE $category IN p.categories
            RETURN count(p) as total
            """
            params = {"category": category, "skip": skip, "limit": page_size}
        else:
            query = """
            MATCH (p:Paper)
            RETURN p
            ORDER BY p.published_date DESC
            SKIP $skip
            LIMIT $limit
            """
            count_query = """
            MATCH (p:Paper)
            RETURN count(p) as total
            """
            params = {"skip": skip, "limit": page_size}
        
        # Execute queries
        records = await neo4j.execute_query(query, params)
        count_result = await neo4j.execute_query(count_query, params)
        
        total = count_result[0].get("total", 0) if count_result else 0
        
        # Convert to response model
        papers = [_paper_record_to_summary(r.get("p", {})) for r in records]
        
        return PaperListResponse(
            papers=papers,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(skip + page_size) < total,
            has_prev=page > 1,
        )
        
    except Neo4jError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{arxiv_id}", response_model=PaperDetail)
async def get_paper(
    arxiv_id: str,
    include_citations: bool = Query(False, description="Include citing papers"),
    include_references: bool = Query(False, description="Include referenced papers"),
    neo4j: Neo4jClient = Depends(get_neo4j_client),
) -> PaperDetail:
    """
    Get detailed paper information by arXiv ID.
    Optionally include citations and references.
    """
    try:
        # Get main paper
        query = """
        MATCH (p:Paper {arxiv_id: $arxiv_id})
        RETURN p
        """
        records = await neo4j.execute_query(query, {"arxiv_id": arxiv_id})
        
        if not records:
            raise HTTPException(status_code=404, detail=f"Paper {arxiv_id} not found")
        
        paper_data = records[0].get("p", {})
        paper = _paper_record_to_detail(paper_data)
        
        # Get citations if requested
        if include_citations:
            citations_query = """
            MATCH (citing:Paper)-[:CITES]->(p:Paper {arxiv_id: $arxiv_id})
            RETURN citing
            LIMIT 50
            """
            citation_records = await neo4j.execute_query(
                citations_query,
                {"arxiv_id": arxiv_id},
            )
            paper.citations = [
                _paper_record_to_summary(r.get("citing", {}))
                for r in citation_records
            ]
        
        # Get references if requested
        if include_references:
            references_query = """
            MATCH (p:Paper {arxiv_id: $arxiv_id})-[:CITES]->(ref:Paper)
            RETURN ref
            LIMIT 50
            """
            reference_records = await neo4j.execute_query(
                references_query,
                {"arxiv_id": arxiv_id},
            )
            paper.references = [
                _paper_record_to_summary(r.get("ref", {}))
                for r in reference_records
            ]
        
        return paper
        
    except Neo4jError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/batch", response_model=PaperBatchResponse)
async def get_papers_batch(
    request: PaperBatchRequest,
    neo4j: Neo4jClient = Depends(get_neo4j_client),
) -> PaperBatchResponse:
    """
    Fetch multiple papers by arXiv IDs.
    Returns found papers and list of not found IDs.
    """
    try:
        query = """
        MATCH (p:Paper)
        WHERE p.arxiv_id IN $arxiv_ids
        RETURN p
        """
        records = await neo4j.execute_query(
            query,
            {"arxiv_ids": request.arxiv_ids},
        )
        
        # Convert to papers
        papers = [_paper_record_to_summary(r.get("p", {})) for r in records]
        found_ids = {p.arxiv_id for p in papers}
        not_found = [aid for aid in request.arxiv_ids if aid not in found_ids]
        
        return PaperBatchResponse(
            papers=papers,
            found=len(papers),
            not_found=not_found,
        )
        
    except Neo4jError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")