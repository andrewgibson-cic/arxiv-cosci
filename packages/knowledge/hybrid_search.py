"""Hybrid search combining vector similarity with graph queries.

Provides unified search that leverages both:
- ChromaDB semantic similarity for relevance ranking
- Neo4j graph structure for relationship-based filtering and expansion
"""

import asyncio
from typing import Any

import structlog

from packages.knowledge.chromadb_client import chromadb_client
from packages.knowledge.neo4j_client import neo4j_client

logger = structlog.get_logger()


async def hybrid_search(
    query: str,
    *,
    n_results: int = 10,
    category_filter: str | None = None,
    expand_citations: bool = False,
    min_similarity: float = 0.5,
) -> list[dict[str, Any]]:
    """Search papers using both vector and graph databases.

    Combines semantic similarity from ChromaDB with graph structure from Neo4j.

    Args:
        query: Natural language search query
        n_results: Maximum results to return
        category_filter: Filter by arXiv category
        expand_citations: Include papers cited by/citing the matches
        min_similarity: Minimum similarity score threshold

    Returns:
        List of papers with combined scores and metadata
    """
    # Get vector search results
    vector_results = chromadb_client.search_papers(
        query,
        n_results=n_results * 2 if expand_citations else n_results,
        category_filter=category_filter,
    )

    # Filter by minimum similarity
    vector_results = [
        r for r in vector_results
        if r.get("similarity", 0) >= min_similarity
    ]

    if not vector_results:
        return []

    arxiv_ids = [r["arxiv_id"] for r in vector_results]

    # Enrich with graph data
    await neo4j_client.connect()
    try:
        enriched_results = await _enrich_with_graph_data(arxiv_ids, vector_results)

        if expand_citations:
            enriched_results = await _expand_citations(enriched_results, n_results)

    finally:
        await neo4j_client.close()

    # Sort by combined score and limit
    enriched_results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
    return enriched_results[:n_results]


async def _enrich_with_graph_data(
    arxiv_ids: list[str],
    vector_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add graph metadata to vector search results."""
    query = """
    UNWIND $ids AS id
    OPTIONAL MATCH (p:Paper {arxiv_id: id})
    OPTIONAL MATCH (a:Author)-[:AUTHORED]->(p)
    OPTIONAL MATCH (p)-[:CITES]->(cited:Paper)
    OPTIONAL MATCH (citing:Paper)-[:CITES]->(p)
    RETURN id,
           p.title AS title,
           collect(DISTINCT a.name) AS authors,
           count(DISTINCT cited) AS outgoing_citations,
           count(DISTINCT citing) AS incoming_citations
    """

    async with neo4j_client.session() as session:
        result = await session.run(query, {"ids": arxiv_ids})
        records = await result.data()

    # Create lookup
    graph_data = {r["id"]: r for r in records}

    # Merge results
    enriched = []
    for vr in vector_results:
        arxiv_id = vr["arxiv_id"]
        gd = graph_data.get(arxiv_id, {})

        combined = {
            **vr,
            "authors": gd.get("authors", []),
            "outgoing_citations": gd.get("outgoing_citations", 0),
            "incoming_citations": gd.get("incoming_citations", 0),
            "in_graph": gd.get("title") is not None,
        }

        # Calculate combined score (similarity + citation influence)
        similarity = vr.get("similarity", 0)
        citation_boost = min(0.1, (combined["incoming_citations"] or 0) * 0.01)
        combined["combined_score"] = similarity + citation_boost

        enriched.append(combined)

    return enriched


async def _expand_citations(
    results: list[dict[str, Any]],
    max_total: int,
) -> list[dict[str, Any]]:
    """Expand results with highly-cited related papers."""
    arxiv_ids = [r["arxiv_id"] for r in results]

    query = """
    MATCH (p:Paper)-[:CITES]-(related:Paper)
    WHERE p.arxiv_id IN $ids
      AND NOT related.arxiv_id IN $ids
    WITH related, count(*) AS connection_count
    ORDER BY connection_count DESC
    LIMIT $limit
    RETURN related.arxiv_id AS arxiv_id,
           related.title AS title,
           connection_count
    """

    async with neo4j_client.session() as session:
        result = await session.run(
            query,
            {"ids": arxiv_ids, "limit": max_total - len(results)},
        )
        records = await result.data()

    # Add related papers with lower scores
    for record in records:
        results.append({
            "arxiv_id": record["arxiv_id"],
            "title": record.get("title", ""),
            "similarity": 0,
            "combined_score": 0.3 + min(0.2, record["connection_count"] * 0.05),
            "source": "citation_expansion",
            "connection_count": record["connection_count"],
        })

    return results


async def find_research_path(
    start_arxiv_id: str,
    end_arxiv_id: str,
    max_hops: int = 5,
) -> list[dict[str, Any]] | None:
    """Find the shortest citation path between two papers.

    Args:
        start_arxiv_id: Starting paper ID
        end_arxiv_id: Target paper ID
        max_hops: Maximum path length to search

    Returns:
        List of papers in the path, or None if no path exists
    """
    query = """
    MATCH path = shortestPath(
        (start:Paper {arxiv_id: $start_id})-[:CITES*1..$max_hops]-(end:Paper {arxiv_id: $end_id})
    )
    UNWIND nodes(path) AS paper
    RETURN paper.arxiv_id AS arxiv_id,
           paper.title AS title
    """

    await neo4j_client.connect()
    try:
        async with neo4j_client.session() as session:
            result = await session.run(
                query,
                {"start_id": start_arxiv_id, "end_id": end_arxiv_id, "max_hops": max_hops},
            )
            records = await result.data()

        if not records:
            return None

        return [{"arxiv_id": r["arxiv_id"], "title": r["title"]} for r in records]

    finally:
        await neo4j_client.close()


async def find_structural_holes(
    category: str,
    min_cluster_size: int = 5,
) -> list[dict[str, Any]]:
    """Find gaps in the citation network within a category.

    Identifies clusters of papers that could be connected but aren't,
    suggesting potential research opportunities.

    Args:
        category: arXiv category to analyze
        min_cluster_size: Minimum papers for a valid cluster

    Returns:
        List of potential research gaps with suggested connections
    """
    query = """
    MATCH (p:Paper)-[:BELONGS_TO]->(:Category {id: $category})
    WHERE NOT exists((p)-[:CITES]-())
    WITH collect(p) AS isolated_papers
    WHERE size(isolated_papers) >= $min_size
    RETURN [paper IN isolated_papers | {
        arxiv_id: paper.arxiv_id,
        title: paper.title
    }] AS papers
    """

    await neo4j_client.connect()
    try:
        async with neo4j_client.session() as session:
            result = await session.run(
                query,
                {"category": category, "min_size": min_cluster_size},
            )
            record = await result.single()

        if not record:
            return []

        papers = record["papers"]

        # For each isolated paper, find semantically similar papers it could cite
        gaps = []
        for paper in papers[:10]:  # Limit analysis
            similar = chromadb_client.get_similar_papers(paper["arxiv_id"], n_results=3)
            if similar:
                gaps.append({
                    "isolated_paper": paper,
                    "potential_connections": similar,
                })

        return gaps

    finally:
        await neo4j_client.close()
