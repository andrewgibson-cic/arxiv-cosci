"""Tests for Semantic Scholar API client.

This module tests the S2Client with mocked API responses
to avoid requiring actual API access during testing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from packages.ingestion.s2_client import S2Client
from packages.ingestion.models import PaperMetadata


@pytest.fixture
def mock_s2_response():
    """Sample Semantic Scholar API response."""
    return {
        "paperId": "abc123",
        "externalIds": {"ArXiv": "2401.12345"},
        "title": "Quantum Error Correction in Topological Codes",
        "abstract": "This paper presents a novel approach to quantum error correction using topological codes.",
        "year": 2024,
        "authors": [
            {"name": "Alice Smith", "authorId": "1"},
            {"name": "Bob Johnson", "authorId": "2"},
        ],
        "citationCount": 42,
        "influentialCitationCount": 15,
        "publicationDate": "2024-01-23",
        "fieldsOfStudy": ["Physics", "Computer Science"],
        "s2FieldsOfStudy": [
            {"category": "Physics", "source": "s2-fos-model"},
            {"category": "Computer Science", "source": "s2-fos-model"},
        ],
        "tldr": {"text": "Novel quantum error correction approach"},
        "citations": [],
        "references": [],
    }


@pytest.fixture
def mock_citation_response():
    """Sample citation data from S2 API."""
    return {
        "offset": 0,
        "next": 10,
        "data": [
            {
                "contexts": ["Previous work on quantum codes [1]"],
                "intents": ["methodology"],
                "isInfluential": True,
                "citingPaper": {
                    "paperId": "def456",
                    "title": "Advanced Quantum Codes",
                    "authors": [{"name": "Carol Davis"}],
                },
            }
        ],
    }


class TestS2ClientInitialization:
    """Tests for S2Client initialization."""

    def test_init_without_api_key(self):
        """Test client initialization without API key."""
        client = S2Client()
        assert client.api_key is None
        assert client.base_url == "https://api.semanticscholar.org/graph/v1"

    def test_init_with_api_key(self):
        """Test client initialization with API key."""
        client = S2Client(api_key="test_key_123")
        assert client.api_key == "test_key_123"
        assert "x-api-key" in client.session.headers


class TestGetPaper:
    """Tests for fetching individual papers."""

    @pytest.mark.asyncio
    async def test_get_paper_by_arxiv_id_success(self, mock_s2_response):
        """Test successful paper retrieval by arXiv ID."""
        client = S2Client()

        with patch.object(client.session, "get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_s2_response)
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await client.get_paper_by_arxiv_id("2401.12345")

            assert result is not None
            assert result["title"] == "Quantum Error Correction in Topological Codes"
            assert result["externalIds"]["ArXiv"] == "2401.12345"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_paper_by_arxiv_id_not_found(self):
        """Test paper not found (404 response)."""
        client = S2Client()

        with patch.object(client.session, "get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await client.get_paper_by_arxiv_id("9999.99999")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_paper_rate_limit_retry(self):
        """Test rate limit handling with retry."""
        client = S2Client()

        with patch.object(client.session, "get") as mock_get:
            # First call returns 429, second succeeds
            mock_response_429 = AsyncMock()
            mock_response_429.status = 429
            mock_response_429.headers = {"Retry-After": "1"}

            mock_response_200 = AsyncMock()
            mock_response_200.status = 200
            mock_response_200.json = AsyncMock(return_value={"title": "Test"})

            mock_get.return_value.__aenter__.side_effect = [
                mock_response_429,
                mock_response_200,
            ]

            with patch("asyncio.sleep") as mock_sleep:
                result = await client.get_paper_by_arxiv_id("2401.12345")

                assert result is not None
                assert mock_sleep.called
                assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_paper_by_s2_id(self, mock_s2_response):
        """Test fetching paper by S2 paper ID."""
        client = S2Client()

        with patch.object(client.session, "get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_s2_response)
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await client.get_paper_by_s2_id("abc123")

            assert result is not None
            assert result["paperId"] == "abc123"


class TestCitationsAndReferences:
    """Tests for fetching citations and references."""

    @pytest.mark.asyncio
    async def test_get_paper_citations(self, mock_citation_response):
        """Test fetching paper citations."""
        client = S2Client()

        with patch.object(client.session, "get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_citation_response)
            mock_get.return_value.__aenter__.return_value = mock_response

            citations = await client.get_paper_citations("2401.12345", limit=10)

            assert len(citations) == 1
            assert citations[0]["citingPaper"]["title"] == "Advanced Quantum Codes"
            assert citations[0]["isInfluential"] is True

    @pytest.mark.asyncio
    async def test_get_paper_references(self):
        """Test fetching paper references."""
        client = S2Client()

        reference_response = {
            "offset": 0,
            "data": [
                {
                    "contexts": ["Building on prior work [5]"],
                    "citedPaper": {
                        "paperId": "ref123",
                        "title": "Foundations of Quantum Computing",
                    },
                }
            ],
        }

        with patch.object(client.session, "get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=reference_response)
            mock_get.return_value.__aenter__.return_value = mock_response

            references = await client.get_paper_references("2401.12345", limit=10)

            assert len(references) == 1
            assert references[0]["citedPaper"]["title"] == "Foundations of Quantum Computing"

    @pytest.mark.asyncio
    async def test_get_citations_empty_result(self):
        """Test fetching citations with no results."""
        client = S2Client()

        with patch.object(client.session, "get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"offset": 0, "data": []})
            mock_get.return_value.__aenter__.return_value = mock_response

            citations = await client.get_paper_citations("2401.12345")

            assert citations == []


class TestBulkOperations:
    """Tests for bulk paper retrieval."""

    @pytest.mark.asyncio
    async def test_get_papers_bulk(self, mock_s2_response):
        """Test fetching multiple papers in bulk."""
        client = S2Client()

        bulk_response = [mock_s2_response, mock_s2_response]

        with patch.object(client.session, "post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=bulk_response)
            mock_post.return_value.__aenter__.return_value = mock_response

            arxiv_ids = ["2401.12345", "2402.67890"]
            results = await client.get_papers_bulk(arxiv_ids)

            assert len(results) == 2
            assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_get_papers_bulk_batch_splitting(self):
        """Test bulk retrieval with automatic batching."""
        client = S2Client()

        # Create 150 IDs to test batch splitting (max 500 per batch)
        arxiv_ids = [f"2401.{i:05d}" for i in range(150)]

        with patch.object(client.session, "post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=[{"paperId": "test"}] * 150)
            mock_post.return_value.__aenter__.return_value = mock_response

            results = await client.get_papers_bulk(arxiv_ids)

            # Should make 1 call for 150 papers (under 500 limit)
            assert mock_post.call_count == 1
            assert len(results) == 150


class TestSearchPapers:
    """Tests for paper search functionality."""

    @pytest.mark.asyncio
    async def test_search_papers(self):
        """Test searching papers by query."""
        client = S2Client()

        search_response = {
            "total": 2,
            "offset": 0,
            "data": [
                {"paperId": "1", "title": "Quantum Computing Basics"},
                {"paperId": "2", "title": "Advanced Quantum Algorithms"},
            ],
        }

        with patch.object(client.session, "get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=search_response)
            mock_get.return_value.__aenter__.return_value = mock_response

            results = await client.search_papers("quantum computing", limit=10)

            assert len(results) == 2
            assert results[0]["title"] == "Quantum Computing Basics"

    @pytest.mark.asyncio
    async def test_search_papers_with_filters(self):
        """Test searching with year and field filters."""
        client = S2Client()

        with patch.object(client.session, "get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"total": 0, "data": []})
            mock_get.return_value.__aenter__.return_value = mock_response

            await client.search_papers(
                "quantum",
                limit=10,
                year="2024",
                fields_of_study=["Physics"],
            )

            # Verify query parameters were included
            call_args = mock_get.call_args
            assert "year=2024" in str(call_args)


class TestDataConversion:
    """Tests for converting S2 data to internal models."""

    def test_paper_to_metadata(self, mock_s2_response):
        """Test converting S2 paper to PaperMetadata."""
        client = S2Client()

        metadata = client.paper_to_metadata(mock_s2_response)

        assert isinstance(metadata, PaperMetadata)
        assert metadata.id == "2401.12345"
        assert metadata.title == "Quantum Error Correction in Topological Codes"
        assert metadata.authors == "Alice Smith, Bob Johnson"
        assert metadata.primary_category == "Physics"
        assert len(metadata.categories) == 2

    def test_paper_to_metadata_missing_fields(self):
        """Test conversion with missing optional fields."""
        client = S2Client()

        minimal_paper = {
            "paperId": "test123",
            "externalIds": {"ArXiv": "2401.00001"},
            "title": "Test Paper",
            "abstract": None,
            "authors": [],
            "year": 2024,
        }

        metadata = client.paper_to_metadata(minimal_paper)

        assert metadata.id == "2401.00001"
        assert metadata.authors == ""
        assert metadata.abstract == ""

    def test_paper_to_metadata_no_arxiv_id(self):
        """Test conversion when paper has no arXiv ID."""
        client = S2Client()

        paper_without_arxiv = {
            "paperId": "s2paper123",
            "externalIds": {"DOI": "10.1234/test"},
            "title": "Non-arXiv Paper",
            "abstract": "Test",
            "authors": [{"name": "Test Author"}],
            "year": 2024,
        }

        metadata = client.paper_to_metadata(paper_without_arxiv)

        # Should use S2 paper ID as fallback
        assert metadata.id == "s2paper123"


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test handling of network errors."""
        client = S2Client()

        with patch.object(client.session, "get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            result = await client.get_paper_by_arxiv_id("2401.12345")

            assert result is None

    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of invalid JSON in response."""
        client = S2Client()

        with patch.object(client.session, "get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(side_effect=ValueError("Invalid JSON"))
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await client.get_paper_by_arxiv_id("2401.12345")

            assert result is None

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        client = S2Client(max_retries=2)

        with patch.object(client.session, "get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_get.return_value.__aenter__.return_value = mock_response

            with patch("asyncio.sleep"):
                result = await client.get_paper_by_arxiv_id("2401.12345")

                assert result is None
                assert mock_get.call_count == 2  # Initial + 1 retry


class TestClientCleanup:
    """Tests for client session cleanup."""

    @pytest.mark.asyncio
    async def test_close_session(self):
        """Test proper session closure."""
        client = S2Client()

        with patch.object(client.session, "close") as mock_close:
            mock_close.return_value = AsyncMock()
            await client.close()

            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client as async context manager."""
        async with S2Client() as client:
            assert client.session is not None

        # Session should be closed after exiting context
        # (Would need to check session state in real implementation)


class TestRateLimiting:
    """Tests for rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff on retries."""
        client = S2Client()

        with patch.object(client.session, "get") as mock_get:
            # Simulate 3 failures then success
            responses = [
                AsyncMock(status=500),
                AsyncMock(status=500),
                AsyncMock(status=500),
                AsyncMock(status=200, json=AsyncMock(return_value={"title": "Test"})),
            ]

            mock_get.return_value.__aenter__.side_effect = responses

            with patch("asyncio.sleep") as mock_sleep:
                result = await client.get_paper_by_arxiv_id("2401.12345")

                # Should have called sleep with increasing delays
                assert mock_sleep.call_count >= 2

    @pytest.mark.asyncio
    async def test_retry_after_header(self):
        """Test respecting Retry-After header."""
        client = S2Client()

        with patch.object(client.session, "get") as mock_get:
            mock_response_429 = AsyncMock()
            mock_response_429.status = 429
            mock_response_429.headers = {"Retry-After": "5"}

            mock_response_200 = AsyncMock()
            mock_response_200.status = 200
            mock_response_200.json = AsyncMock(return_value={"title": "Test"})

            mock_get.return_value.__aenter__.side_effect = [
                mock_response_429,
                mock_response_200,
            ]

            with patch("asyncio.sleep") as mock_sleep:
                await client.get_paper_by_arxiv_id("2401.12345")

                # Should sleep for at least the Retry-After duration
                assert any(call[0][0] >= 5 for call in mock_sleep.call_args_list)
