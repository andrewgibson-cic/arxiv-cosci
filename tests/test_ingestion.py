"""Tests for the ingestion package."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from packages.ingestion.models import (
    ArxivCategory,
    ArxivPaper,
    Citation,
    CitationIntent,
    Concept,
    ConceptType,
    PaperMetadata,
    ParsedPaper,
    ParserType,
    Section,
)


class TestPaperMetadata:
    """Tests for PaperMetadata model."""

    def test_basic_creation(self) -> None:
        """Test creating a basic paper metadata object."""
        metadata = PaperMetadata(
            id="2401.12345",
            title="Test Paper",
            authors="John Doe, Jane Smith",
            categories="quant-ph hep-th",
            abstract="This is a test abstract.",
            update_date="2024-01-15",
        )

        assert metadata.id == "2401.12345"
        assert metadata.title == "Test Paper"
        assert metadata.primary_category == "quant-ph"
        assert metadata.category_list == ["quant-ph", "hep-th"]
        assert metadata.arxiv_url == "https://arxiv.org/abs/2401.12345"
        assert metadata.pdf_url == "https://arxiv.org/pdf/2401.12345.pdf"

    def test_author_list_from_parsed(self) -> None:
        """Test extracting author names from parsed authors."""
        metadata = PaperMetadata(
            id="2401.12345",
            title="Test Paper",
            authors="Doe, John and Smith, Jane",
            categories="quant-ph",
            abstract="",
            update_date="2024-01-15",
            authors_parsed=[["Doe", "John", ""], ["Smith", "Jane", ""]],
        )

        assert metadata.author_list == ["John Doe", "Jane Smith"]

    def test_category_normalization(self) -> None:
        """Test that comma-separated categories are normalized."""
        metadata = PaperMetadata(
            id="2401.12345",
            title="Test",
            authors="Author",
            categories="quant-ph,hep-th, math.QA",  # Mixed separators
            abstract="",
            update_date="2024-01-15",
        )

        assert "quant-ph" in metadata.categories
        assert len(metadata.category_list) == 3


class TestArxivPaper:
    """Tests for ArxivPaper model."""

    def test_with_pdf_path(self) -> None:
        """Test paper with PDF path."""
        metadata = PaperMetadata(
            id="2401.12345",
            title="Test",
            authors="Author",
            categories="quant-ph",
            abstract="",
            update_date="2024-01-15",
        )

        paper = ArxivPaper(
            metadata=metadata,
            pdf_path=Path("/tmp/2401.12345.pdf"),
            downloaded_at=datetime.now(),
        )

        assert paper.arxiv_id == "2401.12345"
        assert paper.pdf_path is not None


class TestParsedPaper:
    """Tests for ParsedPaper model."""

    def test_from_metadata(self) -> None:
        """Test creating ParsedPaper from metadata."""
        metadata = PaperMetadata(
            id="2401.12345",
            title="Test Paper",
            authors="John Doe",
            categories="quant-ph math.QA",
            abstract="Test abstract",
            update_date="2024-01-15",
        )

        parsed = ParsedPaper.from_metadata(metadata)

        assert parsed.arxiv_id == "2401.12345"
        assert parsed.title == "Test Paper"
        assert parsed.categories == ["quant-ph", "math.QA"]

    def test_with_sections(self) -> None:
        """Test paper with parsed sections."""
        parsed = ParsedPaper(
            arxiv_id="2401.12345",
            title="Test",
            abstract="Abstract",
            authors=["John Doe"],
            categories=["quant-ph"],
            sections=[
                Section(title="Introduction", content="Intro text", level=1),
                Section(title="Methods", content="Methods text", level=1),
            ],
        )

        assert len(parsed.sections) == 2
        assert parsed.sections[0].title == "Introduction"


class TestSection:
    """Tests for Section model."""

    def test_with_equations(self) -> None:
        """Test section with equations."""
        section = Section(
            title="Theory",
            content="The Hamiltonian is given by...",
            level=1,
            equations=["H = \\sum_i \\sigma_i^z", "E = mc^2"],
        )

        assert len(section.equations) == 2


class TestCitation:
    """Tests for Citation model."""

    def test_arxiv_citation(self) -> None:
        """Test citation with arXiv ID."""
        citation = Citation(
            raw_text="arXiv:2301.00001",
            arxiv_id="2301.00001",
            context="As shown in [1]...",
            intent=CitationIntent.METHOD,
        )

        assert citation.arxiv_id == "2301.00001"
        assert citation.intent == CitationIntent.METHOD

    def test_doi_citation(self) -> None:
        """Test citation with DOI."""
        citation = Citation(
            raw_text="10.1103/PhysRevLett.123.456",
            doi="10.1103/PhysRevLett.123.456",
        )

        assert citation.doi is not None
        assert citation.intent == CitationIntent.UNKNOWN


class TestConcept:
    """Tests for Concept model."""

    def test_paper_count(self) -> None:
        """Test concept paper count."""
        concept = Concept(
            name="Transformer",
            concept_type=ConceptType.ALGORITHM,
            paper_ids=["2401.00001", "2401.00002", "2401.00003"],
        )

        assert concept.paper_count == 3


class TestKaggleLoader:
    """Tests for kaggle_loader module."""

    def test_is_physics_math_paper(self) -> None:
        """Test physics/math category detection."""
        from packages.ingestion.kaggle_loader import is_physics_math_paper

        assert is_physics_math_paper("quant-ph") is True
        assert is_physics_math_paper("hep-th gr-qc") is True
        assert is_physics_math_paper("math.QA") is True
        assert is_physics_math_paper("cs.AI") is False
        assert is_physics_math_paper("econ.EM") is False

    def test_stream_kaggle_metadata(self) -> None:
        """Test streaming metadata from file."""
        from packages.ingestion.kaggle_loader import stream_kaggle_metadata

        # Create test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_data = [
                {
                    "id": "2401.00001",
                    "title": "Quantum Paper",
                    "authors": "Author",
                    "categories": "quant-ph",
                    "abstract": "Abstract",
                    "update_date": "2024-01-15",
                },
                {
                    "id": "2401.00002",
                    "title": "CS Paper",
                    "authors": "Author",
                    "categories": "cs.AI",
                    "abstract": "Abstract",
                    "update_date": "2024-01-15",
                },
            ]
            for item in test_data:
                f.write(json.dumps(item) + "\n")
            temp_path = Path(f.name)

        try:
            # Filter physics/math
            papers = list(stream_kaggle_metadata(temp_path, filter_physics_math=True))
            assert len(papers) == 1
            assert papers[0].id == "2401.00001"

            # No filter
            papers = list(stream_kaggle_metadata(temp_path, filter_physics_math=False))
            assert len(papers) == 2
        finally:
            temp_path.unlink()


class TestTextExtractor:
    """Tests for text_extractor module."""

    def test_arxiv_id_pattern(self) -> None:
        """Test arXiv ID regex pattern."""
        from packages.ingestion.text_extractor import ARXIV_ID_PATTERN

        # New format
        match = ARXIV_ID_PATTERN.search("See arXiv:2401.12345 for details")
        assert match is not None
        assert match.group(1) == "2401.12345"

        # With version
        match = ARXIV_ID_PATTERN.search("arxiv:2401.12345v2")
        assert match is not None
        assert "2401.12345" in match.group(1)

        # Old format
        match = ARXIV_ID_PATTERN.search("hep-th/9901001")
        assert match is not None

    def test_doi_pattern(self) -> None:
        """Test DOI regex pattern."""
        from packages.ingestion.text_extractor import DOI_PATTERN

        match = DOI_PATTERN.search("DOI: 10.1103/PhysRevLett.123.456")
        assert match is not None
        assert "10.1103" in match.group(0)

    def test_section_detection(self) -> None:
        """Test section header detection."""
        from packages.ingestion.text_extractor import PyMuPDFExtractor

        extractor = PyMuPDFExtractor()

        text = """
1. Introduction

This is the introduction.

2. Methods

This is the methods section.

3. Results

These are the results.
"""
        sections = extractor.extract_sections(text)
        assert len(sections) >= 3
        assert any(s.title == "Introduction" for s in sections)


@pytest.mark.asyncio
class TestPDFDownloader:
    """Tests for pdf_downloader module."""

    async def test_rate_limiter(self) -> None:
        """Test rate limiter enforces minimum interval."""
        import time

        from packages.ingestion.pdf_downloader import RateLimiter

        limiter = RateLimiter(min_interval=0.1)

        start = time.time()
        await limiter.acquire()
        await limiter.acquire()
        elapsed = time.time() - start

        assert elapsed >= 0.1

    async def test_get_pdf_path(self) -> None:
        """Test PDF path generation."""
        from packages.ingestion.pdf_downloader import ArxivDownloader

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = ArxivDownloader(Path(tmpdir))

            path = downloader._get_pdf_path("2401.12345")
            assert "2401" in str(path)
            assert path.suffix == ".pdf"

            # Old format
            path = downloader._get_pdf_path("hep-th/9901001")
            assert "hep-th_9901001" in str(path)
