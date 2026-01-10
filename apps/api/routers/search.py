"""
Search Router
Endpoints for semantic and hybrid search.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from apps.api.dependencies import get_neo4j_client, get_chromadb_client, get_settings_cached
from apps.api.config import Settings
from apps.api.schemas.search import SearchResponse, SearchResult, SimilarPapersResponse
from apps.api.schemas.paper import PaperSummary
from packages.knowledge.neo4j_client import Neo4jClient
from packages.knowledge.chromadb_client import ChromaDBClient


router = APIRouter()


@router.get("/semantic", response_model=SearchResponse)
async def semantic_search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    chroma: ChromaDBClient = Depends(get_chromadb_client),
    neo4j: Neo4jClient = Depends(get_neo4j_client),
    settings: Settings = Depends(get_settings_cached),
) -> SearchResponse:
    """
    Semantic search using vector embeddings.
    Finds papers semantically similar to the query.
    """
    try:
        # Limit search results
        limit = min(limit, settings.max_search_limit)
        
        # Perform semantic search via ChromaDB
        results = chroma.search(query_text=q, n_results=limit)
        
        if not results or not results.get("ids"):
            return SearchResponse(
                results=[],
                query=q,
                total=0,
                search_type="semantic",
            )
        
        # Get paper IDs and distances
        paper_ids = results["ids"][0] if results["ids"] else []
        distances = results["distances"][0] if results.get("distances") else []
        
        if not paper_ids:
            return SearchResponse(
                results=[],
                query=q,
                total=0,
                search_type="semantic",
            )
        
        # Fetch paper details from Neo4j
        query_neo4j = """
        MATCH (p:Paper)
        WHERE p.arxiv_id IN $arxiv_ids
        RETURN p
        """
        records = await neo4j.execute_query(query_neo4j, {"arxiv_ids": paper_ids})
        
        # Create paper map
        papers_map = {
            r.get("p", {}).get("arxiv_id"): r.get("p", {})
            for r in records
        }
        
        # Build results with scores
        search_results = []
        for arxiv_id, distance in zip(paper_ids, distances):
            if arxiv_id in papers_map:
                paper_data = papers_map[arxiv_id]
                # Convert distance to similarity score (0-1, higher is better)
                # ChromaDB uses cosine distance, so similarity = 1 - distance
                score = max(0.0, min(1.0, 1.0 - distance))
                
                search_results.append(
                    SearchResult(
                        paper=PaperSummary(
                            arxiv_id=paper_data.get("arxiv_id", ""),
                            title=paper_data.get("title", ""),
                            abstract=paper_data.get("abstract"),
                            authors=paper_data.get("authors", []),
                            categories=paper_data.get("categories", []),
                            published_date=paper_data.get("published_date"),
                            citation_count=paper_data.get("citation_count"),
                        ),
                        score=score,
                    )
                )
        
        return SearchResponse(
            results=search_results,
            query=q,
            total=len(search_results),
            search_type="semantic",
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.get("/hybrid", response_model=SearchResponse)
async def hybrid_search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    chroma: ChromaDBClient = Depends(get_chromadb_client),
    neo4j: Neo4jClient = Depends(get_neo4j_client),
    settings: Settings = Depends(get_settings_cached),
) -> SearchResponse:
    """
    Hybrid search combining vector similarity and graph structure.
    Boosts papers that are semantically similar AND highly cited.
    """
    try:
        # Limit search results
        limit = min(limit, settings.max_search_limit)
        
        # Perform semantic search (get more results to rerank)
        results = chroma.search(query_text=q, n_results=limit * 2)
        
        if not results or not results.get("ids"):
            return SearchResponse(
                results=[],
                query=q,
                total=0,
                search_type="hybrid",
            )
        
        paper_ids = results["ids"][0] if results["ids"] else []
        distances = results["distances"][0] if results.get("distances") else []
        
        if not paper_ids:
            return SearchResponse(
                results=[],
                query=q,
                total=0,
                search_type="hybrid",
            )
        
        # Fetch paper details with citation counts from Neo4j
        query_neo4j = """
        MATCH (p:Paper)
        WHERE p.arxiv_id IN $arxiv_ids
        OPTIONAL MATCH (citing:Paper)-[:CITES]->(p)
        WITH p, count(citing) as citation_count
        RETURN p, citation_count
        """
        records = await neo4j.execute_query(query_neo4j, {"arxiv_ids": paper_ids})
        
        # Create paper map with citation counts
        papers_map = {}
        max_citations = 1
        for r in records:
            paper_data = r.get("p", {})
            arxiv_id = paper_data.get("arxiv_id")
            if arxiv_id:
                citations = r.get("citation_count", 0)
                papers_map[arxiv_id] = (paper_data, citations)
                max_citations = max(max_citations, citations)
        
        # Build results with hybrid scores
        search_results = []
        for arxiv_id, distance in zip(paper_ids, distances):
            if arxiv_id in papers_map:
                paper_data, citations = papers_map[arxiv_id]
                
                # Semantic similarity score (0-1)
                semantic_score = max(0.0, min(1.0, 1.0 - distance))
                
                # Citation score (0-1, normalized)
                citation_score = citations / max_citations if max_citations > 0 else 0
                
                # Hybrid score: 70% semantic, 30% citations
                hybrid_score = 0.7 * semantic_score + 0.3 * citation_score
                
                search_results.append(
                    SearchResult(
                        paper=PaperSummary(
                            arxiv_id=paper_data.get("arxiv_id", ""),
                            title=paper_data.get("title", ""),
                            abstract=paper_data.get("abstract"),
                            authors=paper_data.get("authors", []),
                            categories=paper_data.get("categories", []),
                            published_date=paper_data.get("published_date"),
                            citation_count=citations,
                        ),
                        score=hybrid_score,
                    )
                )
        
        # Sort by hybrid score and limit
        search_results.sort(key=lambda x: x.score, reverse=True)
        search_results = search_results[:limit]
        
        return SearchResponse(
            results=search_results,
            query=q,
            total=len(search_results),
            search_type="hybrid",
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.get("/similar/{arxiv_id}", response_model=SimilarPapersResponse)
async def find_similar_papers(
    arxiv_id: str,
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    chroma: ChromaDBClient = Depends(get_chromadb_client),
    neo4j: Neo4jClient = Depends(get_neo4j_client),
    settings: Settings = Depends(get_settings_cached),
) -> SimilarPapersResponse:
    """
    Find papers similar to a given paper using its embedding.
    """
    try:
        # Limit search results
        limit = min(limit, settings.max_search_limit)
        
        # Get the paper's abstract for semantic search
        query_paper = """
        MATCH (p:Paper {arxiv_id: $arxiv_id})
        RETURN p.abstract as abstract
        """
        records = await neo4j.execute_query(query_paper, {"arxiv_id": arxiv_id})
        
        if not records or not records[0].get("abstract"):
            raise HTTPException(
                status_code=404,
                detail=f"Paper {arxiv_id} not found or has no abstract",
            )
        
        abstract = records[0]["abstract"]
        
        # Search for similar papers
        results = chroma.search(query_text=abstract, n_results=limit + 1)
        
        if not results or not results.get("ids"):
            return SimilarPapersResponse(
                arxiv_id=arxiv_id,
                similar_papers=[],
                total=0,
            )
        
        paper_ids = results["ids"][0] if results["ids"] else []
        distances = results["distances"][0] if results.get("distances") else []
        
        # Filter out the query paper itself
        filtered_results = [
            (pid, dist) for pid, dist in zip(paper_ids, distances)
            if pid != arxiv_id
        ][:limit]
        
        if not filtered_results:
            return SimilarPapersResponse(
                arxiv_id=arxiv_id,
                similar_papers=[],
                total=0,
            )
        
        # Fetch paper details
        similar_ids = [pid for pid, _ in filtered_results]
        query_neo4j = """
        MATCH (p:Paper)
        WHERE p.arxiv_id IN $arxiv_ids
        RETURN p
        """
        records = await neo4j.execute_query(query_neo4j, {"arxiv_ids": similar_ids})
        
        papers_map = {
            r.get("p", {}).get("arxiv_id"): r.get("p", {})
            for r in records
        }
        
        # Build results
        similar_papers = []
        for pid, distance in filtered_results:
            if pid in papers_map:
                paper_data = papers_map[pid]
                score = max(0.0, min(1.0, 1.0 - distance))
                
                similar_papers.append(
                    SearchResult(
                        paper=PaperSummary(
                            arxiv_id=paper_data.get("arxiv_id", ""),
                            title=paper_data.get("title", ""),
                            abstract=paper_data.get("abstract"),
                            authors=paper_data.get("authors", []),
                            categories=paper_data.get("categories", []),
                            published_date=paper_data.get("published_date"),
                            citation_count=paper_data.get("citation_count"),
                        ),
                        score=score,
                    )
                )
        
        return SimilarPapersResponse(
            arxiv_id=arxiv_id,
            similar_papers=similar_papers,
            total=len(similar_papers),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")