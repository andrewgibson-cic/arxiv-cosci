"""
FastAPI Dependencies
Provides dependency injection for database clients and other shared resources.
"""
from functools import lru_cache
from typing import AsyncGenerator

from apps.api.config import Settings, get_settings
from packages.knowledge.neo4j_client import Neo4jClient
from packages.knowledge.chromadb_client import ChromaDBClient


@lru_cache
def get_settings_cached() -> Settings:
    """Get cached settings instance."""
    return get_settings()


_neo4j_client: Neo4jClient | None = None
_chromadb_client: ChromaDBClient | None = None


async def get_neo4j_client() -> Neo4jClient:
    """
    Get or create Neo4j client instance.
    Singleton pattern to reuse connection.
    """
    global _neo4j_client
    
    if _neo4j_client is None:
        settings = get_settings_cached()
        _neo4j_client = Neo4jClient(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
    
    return _neo4j_client


async def get_chromadb_client() -> ChromaDBClient:
    """
    Get or create ChromaDB client instance.
    Singleton pattern to reuse client.
    """
    global _chromadb_client
    
    if _chromadb_client is None:
        settings = get_settings_cached()
        _chromadb_client = ChromaDBClient(
            persist_directory=settings.chroma_persist_dir,
        )
    
    return _chromadb_client


async def close_database_connections() -> None:
    """Close all database connections."""
    global _neo4j_client, _chromadb_client
    
    if _neo4j_client:
        await _neo4j_client.close()
        _neo4j_client = None
    
    _chromadb_client = None