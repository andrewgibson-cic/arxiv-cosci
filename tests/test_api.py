"""
Tests for FastAPI API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from apps.api.main import app


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j client."""
    neo4j = AsyncMock()
    neo4j.verify_connection = AsyncMock(return_value=True)
    neo4j.execute_query = AsyncMock(return_value=[])
    neo4j.close = AsyncMock()
    return neo4j


@pytest.fixture
def mock_chroma():
    """Mock ChromaDB client."""
    chroma = MagicMock()
    chroma.get_or_create_collection = MagicMock(return_value="papers")
    chroma.search = MagicMock(return_value={"ids": [[]], "distances": [[]]})
    return chroma


@pytest.fixture
def client(mock_neo4j, mock_chroma):
    """Create test client with mocked dependencies."""
    from apps.api.dependencies import get_neo4j_client, get_chromadb_client
    
    # Override dependencies
    app.dependency_overrides[get_neo4j_client] = lambda: mock_neo4j
    app.dependency_overrides[get_chromadb_client] = lambda: mock_chroma
    
    client = TestClient(app)
    yield client
    
    # Clean up overrides
    app.dependency_overrides.clear()


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "ArXiv Co-Scientist API"
        assert data["version"] == "0.4.0"
        assert data["status"] == "operational"
    
    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "arxiv-cosci-api"


class TestPapersEndpoints:
    """Test papers API endpoints."""
    
    def test_list_papers_empty(self, client, mock_neo4j):
        """Test listing papers with no results."""
        mock_neo4j.execute_query = AsyncMock(return_value=[])
        
        response = client.get("/api/papers")
        assert response.status_code == 200
        data = response.json()
        assert data["papers"] == []
        assert data["total"] == 0
        assert data["page"] == 1
    
    def test_list_papers_with_data(self, client, mock_neo4j):
        """Test listing papers with results."""
        mock_papers = [
            {
                "p": {
                    "arxiv_id": "2401.12345",
                    "title": "Test Paper",
                    "abstract": "Test abstract",
                    "authors": ["Alice Smith"],
                    "categories": ["quant-ph"],
                    "published_date": "2024-01-15",
                    "citation_count": 10,
                }
            }
        ]
        mock_neo4j.execute_query = AsyncMock(side_effect=[
            mock_papers,  # Papers query
            [{"total": 1}],  # Count query
        ])
        
        response = client.get("/api/papers?page=1&page_size=20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["papers"]) == 1
        assert data["papers"][0]["arxiv_id"] == "2401.12345"
        assert data["total"] == 1
    
    def test_get_paper_not_found(self, client, mock_neo4j):
        """Test getting non-existent paper."""
        mock_neo4j.execute_query = AsyncMock(return_value=[])
        
        response = client.get("/api/papers/2404.99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_paper_success(self, client, mock_neo4j):
        """Test getting paper by arXiv ID."""
        mock_paper = [
            {
                "p": {
                    "arxiv_id": "2401.12345",
                    "title": "Test Paper",
                    "abstract": "Test abstract",
                    "authors": ["Alice Smith"],
                    "categories": ["quant-ph"],
                    "published_date": "2024-01-15",
                }
            }
        ]
        mock_neo4j.execute_query = AsyncMock(return_value=mock_paper)
        
        response = client.get("/api/papers/2401.12345")
        assert response.status_code == 200
        data = response.json()
        assert data["arxiv_id"] == "2401.12345"
        assert data["title"] == "Test Paper"
    
    def test_batch_papers(self, client, mock_neo4j):
        """Test batch fetching papers."""
        mock_papers = [
            {
                "p": {
                    "arxiv_id": "2401.12345",
                    "title": "Paper 1",
                    "authors": [],
                    "categories": [],
                }
            }
        ]
        mock_neo4j.execute_query = AsyncMock(return_value=mock_papers)
        
        response = client.post(
            "/api/papers/batch",
            json={"arxiv_ids": ["2401.12345", "2402.99999"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["found"] == 1
        assert "2402.99999" in data["not_found"]


class TestSearchEndpoints:
    """Test search API endpoints."""
    
    def test_semantic_search_empty(self, client, mock_chroma, mock_neo4j):
        """Test semantic search with no results."""
        mock_chroma.search = MagicMock(return_value={"ids": [[]], "distances": [[]]})
        
        response = client.get("/api/search/semantic?q=quantum&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["query"] == "quantum"
        assert data["search_type"] == "semantic"
    
    def test_semantic_search_with_results(self, client, mock_chroma, mock_neo4j):
        """Test semantic search with results."""
        mock_chroma.search = MagicMock(return_value={
            "ids": [["2401.12345"]],
            "distances": [[0.3]],
        })
        
        mock_papers = [
            {
                "p": {
                    "arxiv_id": "2401.12345",
                    "title": "Quantum Paper",
                    "abstract": "About quantum",
                    "authors": ["Alice"],
                    "categories": ["quant-ph"],
                    "published_date": "2024-01-15",
                }
            }
        ]
        mock_neo4j.execute_query = AsyncMock(return_value=mock_papers)
        
        response = client.get("/api/search/semantic?q=quantum&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["paper"]["arxiv_id"] == "2401.12345"
        assert 0 <= data["results"][0]["score"] <= 1
    
    def test_hybrid_search(self, client, mock_chroma, mock_neo4j):
        """Test hybrid search combining semantic + citations."""
        mock_chroma.search = MagicMock(return_value={
            "ids": [["2401.12345"]],
            "distances": [[0.2]],
        })
        
        mock_papers = [
            {
                "p": {
                    "arxiv_id": "2401.12345",
                    "title": "Quantum Paper",
                    "authors": [],
                    "categories": [],
                },
                "citation_count": 50,
            }
        ]
        mock_neo4j.execute_query = AsyncMock(return_value=mock_papers)
        
        response = client.get("/api/search/hybrid?q=quantum&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["search_type"] == "hybrid"
    
    def test_similar_papers(self, client, mock_chroma, mock_neo4j):
        """Test finding similar papers."""
        # Mock paper query
        mock_neo4j.execute_query = AsyncMock(side_effect=[
            [{"abstract": "Quantum computing abstract"}],  # Get abstract
            [{  # Get similar papers
                "p": {
                    "arxiv_id": "2402.98765",
                    "title": "Similar Paper",
                    "authors": [],
                    "categories": [],
                }
            }],
        ])
        
        mock_chroma.search = MagicMock(return_value={
            "ids": [["2401.12345", "2402.98765"]],
            "distances": [[0.0, 0.15]],
        })
        
        response = client.get("/api/search/similar/2401.12345?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["arxiv_id"] == "2401.12345"


class TestGraphEndpoints:
    """Test graph API endpoints."""
    
    def test_citation_network(self, client, mock_neo4j):
        """Test citation network query."""
        mock_nodes = [
            {
                "all_nodes": [
                    {
                        "arxiv_id": "2401.12345",
                        "title": "Center Paper",
                        "categories": ["quant-ph"],
                        "published_date": "2024-01-15",
                    }
                ],
                "rels": [],
            }
        ]
        mock_neo4j.execute_query = AsyncMock(side_effect=[
            mock_nodes,  # Network query
            [],  # Edges query
        ])
        
        response = client.get("/api/graph/citations/2401.12345?depth=2")
        assert response.status_code == 200
        data = response.json()
        assert data["center_paper"] == "2401.12345"
        assert "nodes" in data
        assert "edges" in data
    
    def test_clusters(self, client, mock_neo4j):
        """Test paper clustering."""
        mock_clusters = [
            {
                "category": "quant-ph",
                "papers": ["2401.12345", "2402.13579"],
                "size": 2,
            }
        ]
        mock_neo4j.execute_query = AsyncMock(return_value=mock_clusters)
        
        response = client.get("/api/graph/clusters?min_size=5")
        assert response.status_code == 200
        data = response.json()
        assert "clusters" in data
        assert data["algorithm"] == "Category Grouping"


class TestPredictionsEndpoints:
    """Test predictions API endpoints."""
    
    def test_link_predictions(self, client, mock_neo4j):
        """Test link predictions endpoint."""
        mock_predictions = [
            {
                "source": "2401.12345",
                "target": "2402.98765",
                "score": 0.85,
                "reason": "Structural similarity",
            }
        ]
        mock_neo4j.execute_query = AsyncMock(return_value=mock_predictions)
        
        response = client.get("/api/predictions/links?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
    
    def test_hypotheses(self, client, mock_neo4j):
        """Test hypotheses endpoint."""
        mock_hypotheses = [
            {
                "id": "hyp-001",
                "title": "Test Hypothesis",
                "description": "Description",
                "confidence": 0.75,
                "papers": ["2401.12345"],
                "gap_type": "paper",
            }
        ]
        mock_neo4j.execute_query = AsyncMock(return_value=mock_hypotheses)
        
        response = client.get("/api/predictions/hypotheses?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "hypotheses" in data


class TestAPIDocumentation:
    """Test API documentation endpoints."""
    
    def test_openapi_schema(self, client):
        """Test OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "ArXiv Co-Scientist API"
        assert schema["info"]["version"] == "0.4.0"
    
    def test_docs_page(self, client):
        """Test Swagger UI docs page."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert b"swagger" in response.content.lower()
    
    def test_redoc_page(self, client):
        """Test ReDoc page."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert b"redoc" in response.content.lower()