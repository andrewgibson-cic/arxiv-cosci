"""Tests for the knowledge package."""

import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from packages.ingestion.models import (
    Citation,
    CitationIntent,
    ParsedPaper,
    ParserType,
    Section,
)

# Check if sentence-transformers is available (requires Python <3.13)
try:
    import sentence_transformers
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

skip_without_ml = pytest.mark.skipif(
    not HAS_SENTENCE_TRANSFORMERS,
    reason="sentence-transformers not available (requires Python <3.13)",
)


@skip_without_ml
class TestChromaDBClient:
    """Tests for ChromaDBClient."""

    def test_add_and_search_paper(self) -> None:
        """Test adding a paper and searching for it."""
        from packages.knowledge.chromadb_client import ChromaDBClient

        with tempfile.TemporaryDirectory() as tmpdir:
            client = ChromaDBClient(persist_dir=Path(tmpdir))

            paper = ParsedPaper(
                arxiv_id="2401.00001",
                title="Quantum Computing Fundamentals",
                abstract="This paper introduces quantum computing principles.",
                authors=["Alice", "Bob"],
                categories=["quant-ph"],
                full_text="Full paper text here.",
                parser_used=ParserType.PYMUPDF,
            )

            client.add_paper(paper)

            results = client.search_papers("quantum principles", n_results=5)
            assert len(results) >= 1
            assert results[0]["arxiv_id"] == "2401.00001"

    def test_batch_add_papers(self) -> None:
        """Test batch adding papers."""
        from packages.knowledge.chromadb_client import ChromaDBClient

        with tempfile.TemporaryDirectory() as tmpdir:
            client = ChromaDBClient(persist_dir=Path(tmpdir))

            papers = [
                ParsedPaper(
                    arxiv_id=f"2401.0000{i}",
                    title=f"Paper {i}",
                    abstract=f"Abstract for paper {i}.",
                    authors=["Author"],
                    categories=["quant-ph"],
                    parser_used=ParserType.PYMUPDF,
                )
                for i in range(5)
            ]

            count = client.add_papers_batch(papers)
            assert count == 5

            stats = client.get_stats()
            assert stats["papers"] == 5

    def test_category_filter(self) -> None:
        """Test searching with category filter."""
        from packages.knowledge.chromadb_client import ChromaDBClient

        with tempfile.TemporaryDirectory() as tmpdir:
            client = ChromaDBClient(persist_dir=Path(tmpdir))

            papers = [
                ParsedPaper(
                    arxiv_id="2401.00001",
                    title="Quantum Paper",
                    abstract="About quantum.",
                    authors=["A"],
                    categories=["quant-ph"],
                    parser_used=ParserType.PYMUPDF,
                ),
                ParsedPaper(
                    arxiv_id="2401.00002",
                    title="Math Paper",
                    abstract="About math.",
                    authors=["B"],
                    categories=["math.QA"],
                    parser_used=ParserType.PYMUPDF,
                ),
            ]
            client.add_papers_batch(papers)

            results = client.search_papers("paper", category_filter="quant-ph")
            assert len(results) == 1
            assert results[0]["arxiv_id"] == "2401.00001"


class TestNeo4jClient:
    """Tests for Neo4jClient that don't require a running database."""

    def test_client_initialization(self) -> None:
        """Test client initializes with defaults."""
        from packages.knowledge.neo4j_client import Neo4jClient
        import os

        # Save original env vars
        original_uri = os.environ.get("NEO4J_URI")
        original_user = os.environ.get("NEO4J_USER")
        original_password = os.environ.get("NEO4J_PASSWORD")
        
        # Clear env vars for this test
        for key in ["NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"]:
            os.environ.pop(key, None)
        
        try:
            client = Neo4jClient()
            assert client.uri == "bolt://127.0.0.1:7687"
            assert client.auth == ("neo4j", "password")
        finally:
            # Restore original env vars
            if original_uri:
                os.environ["NEO4J_URI"] = original_uri
            if original_user:
                os.environ["NEO4J_USER"] = original_user
            if original_password:
                os.environ["NEO4J_PASSWORD"] = original_password

    def test_client_custom_uri(self) -> None:
        """Test client with custom URI."""
        from packages.knowledge.neo4j_client import Neo4jClient

        client = Neo4jClient(
            uri="bolt://localhost:7688",
            auth=("user", "pass"),
        )
        assert client.uri == "bolt://localhost:7688"
        assert client.auth == ("user", "pass")


class TestParsedPaperForIngestion:
    """Test ParsedPaper model for ingestion compatibility."""

    def test_paper_with_citations(self) -> None:
        """Test paper with citation data."""
        paper = ParsedPaper(
            arxiv_id="2401.00001",
            title="Test Paper",
            abstract="Abstract",
            authors=["Author One", "Author Two"],
            categories=["quant-ph", "math.QA"],
            full_text="Paper content with citations.",
            citations=[
                Citation(
                    raw_text="arXiv:2301.00001",
                    arxiv_id="2301.00001",
                    context="As shown in previous work [1]...",
                    intent=CitationIntent.METHOD,
                ),
                Citation(
                    raw_text="10.1234/test",
                    doi="10.1234/test",
                    context="See also [2]...",
                ),
            ],
            sections=[
                Section(title="Introduction", content="Intro text", level=1),
                Section(title="Methods", content="Methods text", level=1),
            ],
            equations=["E = mc^2", "H|psi> = E|psi>"],
            parser_used=ParserType.PYMUPDF,
            parse_confidence=0.8,
        )

        assert len(paper.citations) == 2
        assert paper.citations[0].arxiv_id == "2301.00001"
        assert len(paper.sections) == 2
        assert len(paper.equations) == 2

    def test_paper_serialization(self) -> None:
        """Test paper can be serialized and deserialized."""
        paper = ParsedPaper(
            arxiv_id="2401.00001",
            title="Test",
            abstract="Abstract",
            authors=["Author"],
            categories=["quant-ph"],
            parser_used=ParserType.PYMUPDF,
        )

        json_str = paper.model_dump_json()
        loaded = ParsedPaper.model_validate_json(json_str)

        assert loaded.arxiv_id == paper.arxiv_id
        assert loaded.title == paper.title


class TestHybridSearchModels:
    """Test models used in hybrid search."""

    def test_citation_intent_values(self) -> None:
        """Test citation intent enum values."""
        assert CitationIntent.METHOD.value == "method"
        assert CitationIntent.BACKGROUND.value == "background"
        assert CitationIntent.RESULT.value == "result"

    def test_parser_type_values(self) -> None:
        """Test parser type enum values."""
        assert ParserType.PYMUPDF.value == "pymupdf"
        assert ParserType.NOUGAT.value == "nougat"
        assert ParserType.MARKER.value == "marker"
