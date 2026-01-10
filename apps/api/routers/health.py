"""
Health Check Router
Endpoints for service health monitoring.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.dependencies import get_neo4j_client, get_chromadb_client
from packages.knowledge.neo4j_client import Neo4jClient
from packages.knowledge.chromadb_client import ChromaDBClient


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    version: str


class DatabaseHealthResponse(BaseModel):
    """Database health check response model."""
    neo4j: dict[str, str]
    chromadb: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.
    Returns service status and version.
    """
    return HealthResponse(
        status="healthy",
        service="arxiv-cosci-api",
        version="0.4.0",
    )


@router.get("/health/db", response_model=DatabaseHealthResponse)
async def database_health_check(
    neo4j: Neo4jClient = Depends(get_neo4j_client),
    chroma: ChromaDBClient = Depends(get_chromadb_client),
) -> DatabaseHealthResponse:
    """
    Database health check endpoint.
    Verifies Neo4j and ChromaDB connections.
    """
    neo4j_status = {"status": "unknown", "message": ""}
    chromadb_status = {"status": "unknown", "message": ""}
    
    # Check Neo4j
    try:
        is_connected = await neo4j.verify_connection()
        if is_connected:
            neo4j_status = {"status": "healthy", "message": "Connected"}
        else:
            neo4j_status = {"status": "unhealthy", "message": "Connection failed"}
    except Exception as e:
        neo4j_status = {"status": "unhealthy", "message": str(e)}
    
    # Check ChromaDB
    try:
        # Simple test: check if collection exists
        collection_name = chroma.get_or_create_collection()
        chromadb_status = {
            "status": "healthy",
            "message": f"Connected (collection: {collection_name})",
        }
    except Exception as e:
        chromadb_status = {"status": "unhealthy", "message": str(e)}
    
    # Return overall health
    overall_healthy = (
        neo4j_status["status"] == "healthy" 
        and chromadb_status["status"] == "healthy"
    )
    
    if not overall_healthy:
        raise HTTPException(
            status_code=503,
            detail={
                "neo4j": neo4j_status,
                "chromadb": chromadb_status,
            },
        )
    
    return DatabaseHealthResponse(
        neo4j=neo4j_status,
        chromadb=chromadb_status,
    )