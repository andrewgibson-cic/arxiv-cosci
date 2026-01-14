"""
Pytest configuration and shared fixtures.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_database_connections():
    """
    Mock database connections for tests that need it.
    Not autouse - tests must explicitly request this fixture.
    """
    # Mock Neo4j
    with patch("packages.knowledge.neo4j_client.Neo4jClient") as mock_neo4j_class:
        mock_neo4j = AsyncMock()
        mock_neo4j.verify_connection = AsyncMock(return_value=True)
        mock_neo4j.execute_query = AsyncMock(return_value=[])
        mock_neo4j.close = AsyncMock()
        mock_neo4j_class.return_value = mock_neo4j
        
        # Mock ChromaDB
        with patch("packages.knowledge.chromadb_client.ChromaDBClient") as mock_chroma_class:
            mock_chroma = MagicMock()
            mock_chroma.get_or_create_collection = MagicMock(return_value=MagicMock())
            mock_chroma.search = MagicMock(return_value={"ids": [[]], "distances": [[]]})
            mock_chroma_class.return_value = mock_chroma
            
            yield {
                "neo4j": mock_neo4j,
                "chroma": mock_chroma
            }


@pytest.fixture
def isolated_neo4j():
    """Provide isolated Neo4j mock for specific tests."""
    mock = AsyncMock()
    mock.verify_connection = AsyncMock(return_value=True)
    mock.execute_query = AsyncMock(return_value=[])
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def isolated_chroma():
    """Provide isolated ChromaDB mock for specific tests."""
    mock = MagicMock()
    mock.get_or_create_collection = MagicMock(return_value=MagicMock())
    mock.search = MagicMock(return_value={"ids": [[]], "distances": [[]]})
    return mock