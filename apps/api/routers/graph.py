"""
Graph Router
Endpoints for citation network and graph queries.
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.dependencies import get_neo4j_client, get_settings_cached
from apps.api.config import Settings
from apps.api.schemas.graph import (
    CitationNetworkResponse,
    GraphNode,
    GraphEdge,
    ClustersResponse,
    ClusterInfo,
)
from packages.knowledge.neo4j_client import Neo4jClient


router = APIRouter()


@router.get("/citations/{arxiv_id}", response_model=CitationNetworkResponse)
async def get_citation_network(
    arxiv_id: str,
    depth: int = Query(2, ge=1, le=5, description="Citation depth"),
    neo4j: Neo4jClient = Depends(get_neo4j_client),
    settings: Settings = Depends(get_settings_cached),
) -> CitationNetworkResponse:
    """
    Get citation network around a paper.
    Returns nodes and edges for visualization.
    """
    try:
        # Limit depth
        depth = min(depth, settings.max_graph_depth)
        
        # Query for citation network (both directions)
        query = """
        MATCH path = (p:Paper {arxiv_id: $arxiv_id})-[:CITES*1..%d]-(related:Paper)
        WITH p, related, relationships(path) as rels
        RETURN 
            collect(DISTINCT p) + collect(DISTINCT related) as all_nodes,
            rels
        LIMIT $max_nodes
        """ % depth
        
        records = await neo4j.execute_query(
            query,
            {"arxiv_id": arxiv_id, "max_nodes": settings.max_graph_nodes},
        )
        
        if not records:
            raise HTTPException(status_code=404, detail=f"Paper {arxiv_id} not found")
        
        # Extract nodes
        nodes_set = set()
        nodes = []
        edges = []
        
        for record in records:
            all_nodes = record.get("all_nodes", [])
            rels = record.get("rels", [])
            
            # Process nodes
            for node_data in all_nodes:
                if not node_data:
                    continue
                    
                node_id = node_data.get("arxiv_id")
                if node_id and node_id not in nodes_set:
                    nodes_set.add(node_id)
                    
                    # Extract year from published_date
                    year = None
                    pub_date = node_data.get("published_date")
                    if pub_date:
                        try:
                            year = int(pub_date.split("-")[0])
                        except (ValueError, IndexError):
                            pass
                    
                    # Get primary category
                    categories = node_data.get("categories", [])
                    category = categories[0] if categories else None
                    
                    nodes.append(
                        GraphNode(
                            id=node_id,
                            label=node_data.get("title", "")[:100],  # Truncate long titles
                            type="paper",
                            category=category,
                            citation_count=node_data.get("citation_count"),
                            year=year,
                        )
                    )
            
            # Process relationships
            for rel in rels:
                if not rel:
                    continue
                # Neo4j relationship has start_node and end_node
                # For now, we'll handle this in a simplified way
                # In production, you'd extract actual node IDs from the relationship
        
        # If we don't have edges from relationships, query them separately
        if not edges:
            edges_query = """
            MATCH (source:Paper)-[r:CITES]->(target:Paper)
            WHERE source.arxiv_id IN $node_ids AND target.arxiv_id IN $node_ids
            RETURN source.arxiv_id as source, target.arxiv_id as target
            """
            node_ids = list(nodes_set)
            edge_records = await neo4j.execute_query(
                edges_query,
                {"node_ids": node_ids},
            )
            
            for edge_rec in edge_records:
                source = edge_rec.get("source")
                target = edge_rec.get("target")
                if source and target:
                    edges.append(
                        GraphEdge(
                            source=source,
                            target=target,
                            type="cites",
                            weight=1.0,
                        )
                    )
        
        return CitationNetworkResponse(
            center_paper=arxiv_id,
            nodes=nodes,
            edges=edges,
            depth=depth,
            total_nodes=len(nodes),
            total_edges=len(edges),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph query error: {str(e)}")


@router.get("/clusters", response_model=ClustersResponse)
async def get_clusters(
    min_size: int = Query(5, ge=1, description="Minimum cluster size"),
    neo4j: Neo4jClient = Depends(get_neo4j_client),
) -> ClustersResponse:
    """
    Get paper clusters/communities using graph algorithms.
    Note: Requires Neo4j Graph Data Science library for advanced clustering.
    This is a simplified version using category grouping.
    """
    try:
        # Simplified clustering by category
        query = """
        MATCH (p:Paper)
        WHERE size(p.categories) > 0
        WITH p.categories[0] as category, collect(p.arxiv_id) as papers
        WHERE size(papers) >= $min_size
        RETURN category, papers, size(papers) as size
        ORDER BY size DESC
        """
        
        records = await neo4j.execute_query(query, {"min_size": min_size})
        
        clusters = []
        for idx, record in enumerate(records):
            category = record.get("category")
            papers = record.get("papers", [])
            size = record.get("size", 0)
            
            clusters.append(
                ClusterInfo(
                    cluster_id=idx,
                    size=size,
                    papers=papers[:100],  # Limit papers returned
                    label=category,
                )
            )
        
        return ClustersResponse(
            clusters=clusters,
            total_clusters=len(clusters),
            algorithm="Category Grouping",
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clustering error: {str(e)}")