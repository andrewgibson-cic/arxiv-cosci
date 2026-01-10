"""
Graph API Schemas
Response models for graph-related endpoints.
"""
from typing import Optional, Literal

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """Graph node representation."""
    id: str = Field(..., description="Node ID (arxiv_id)")
    label: str = Field(..., description="Node label (paper title)")
    type: Literal["paper", "author", "concept"] = "paper"
    category: Optional[str] = None
    citation_count: Optional[int] = None
    year: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "2401.12345",
                "label": "Quantum Error Correction",
                "type": "paper",
                "category": "quant-ph",
                "citation_count": 42,
                "year": 2024,
            }
        }


class GraphEdge(BaseModel):
    """Graph edge representation."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: Literal["cites", "authored_by", "uses_concept"] = "cites"
    weight: float = Field(1.0, description="Edge weight")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source": "2401.12345",
                "target": "2302.98765",
                "type": "cites",
                "weight": 1.0,
            }
        }


class CitationNetworkResponse(BaseModel):
    """Citation network response."""
    center_paper: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    depth: int
    total_nodes: int
    total_edges: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "center_paper": "2401.12345",
                "nodes": [],
                "edges": [],
                "depth": 2,
                "total_nodes": 50,
                "total_edges": 123,
            }
        }


class ClusterInfo(BaseModel):
    """Cluster/community information."""
    cluster_id: int
    size: int
    papers: list[str] = Field(..., description="arXiv IDs in cluster")
    label: Optional[str] = Field(None, description="Cluster label/topic")
    
    class Config:
        json_schema_extra = {
            "example": {
                "cluster_id": 1,
                "size": 25,
                "papers": ["2401.12345", "2402.13579"],
                "label": "Quantum Error Correction",
            }
        }


class ClustersResponse(BaseModel):
    """Response for community detection."""
    clusters: list[ClusterInfo]
    total_clusters: int
    algorithm: str = "Louvain"
    
    class Config:
        json_schema_extra = {
            "example": {
                "clusters": [],
                "total_clusters": 8,
                "algorithm": "Louvain",
            }
        }