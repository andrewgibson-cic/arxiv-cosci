"""Tests for PDF parsing pipeline.

This module tests the PDF parsing infrastructure with mocked services
to avoid requiring actual Marker, Grobid, or PDF files during testing.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from packages.ingestion.models import ParsedPaper, ParserType


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a temporary PDF file path."""
    pdf_file = tmp_path / "test_paper.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 fake pdf content")
    return pdf_file


@pytest.fixture
def sample_markdown():
    """Sample markdown output from parser."""
    return """# Quantum Error Correction in Topological Codes

## Abstract
This paper presents a novel approach to quantum error correction.

## Introduction
Quantum computing requires robust error correction...

## Methods
We propose a new topological code based on...

### Equation 1
$$H = \\sum_i X_i + Y_i$$

## Results
Our approach achieves 99% fidelity...

## Conclusion
The proposed method demonstrates significant improvements.

## References
[1] Smith et al., "Previous work", Nature 2023
"""


@pytest.fixture
def sample_grobid_xml():
    """Sample Grobid TEI XML output."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title>Test Paper Title</title>
            </titleStmt>
            <sourceDesc>
                <biblStruct>
                    <analytic>
                        <author>
                            <persName>
                                <forename>John</forename>
                                <surname>Doe</surname>
                            </persName>
                        </author>
                    </analytic>
                </biblStruct>
            </sourceDesc>
        </fileDesc>
    </teiHeader>
    <text>
        <body>
            <div>
                <head>Introduction</head>
                <p>Sample text with <ref type="bibr">citation</ref></p>
            </div>
        </body>
        <back>
            <div type="references">
                <listBibl>
                    <biblStruct>
                        <analytic>
                            <title>Referenced Paper</title>
                        </analytic>
                    </biblStruct>
                </listBibl>
            </div>
        </back>
    </text>
</TEI>"""


class TestMarkerParser:
    """Tests for Marker PDF parser integration."""

    @patch("packages.ingestion.marker_parser.subprocess.run")
    def test_marker_parse_success(self, mock_run, sample_pdf_path, sample_markdown):
        """Test successful Marker parsing."""
        from packages.ingestion.marker_parser import parse_with_marker

        # Mock subprocess success
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=sample_markdown,
            stderr=""
        )

        result = parse_with_marker(sample_pdf_path)

        assert result is not None
        assert "Quantum Error Correction" in result
        assert "## Abstract" in result
        mock_run.assert_called_once()

    @patch("packages.ingestion.marker_parser.subprocess.run")
    def test_marker_parse_failure(self, mock_run, sample_pdf_path):
        """Test Marker parsing failure."""
        from packages.ingestion.marker_parser import parse_with_marker

        # Mock subprocess failure
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error processing PDF"
        )

        result = parse_with_marker(sample_pdf_path)

        assert result is None

    @patch("packages.ingestion.marker_parser.subprocess.run")
    def test_marker_timeout(self, mock_run, sample_pdf_path):
        """Test Marker parsing timeout."""
        from packages.ingestion.marker_parser import parse_with_marker
        import subprocess

        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="marker_single",
            timeout=300
        )

        result = parse_with_marker(sample_pdf_path, timeout=300)

        assert result is None


class TestGrobidParser:
    """Tests for Grobid citation extraction."""

    @patch("packages.ingestion.grobid_parser.requests.post")
    def test_grobid_parse_success(self, mock_post, sample_pdf_path, sample_grobid_xml):
        """Test successful Grobid parsing."""
        from packages.ingestion.grobid_parser import parse_with_grobid

        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_grobid_xml
        mock_post.return_value = mock_response

        result = parse_with_grobid(sample_pdf_path)

        assert result is not None
        assert "Test Paper Title" in result
        mock_post.assert_called_once()

    @patch("packages.ingestion.grobid_parser.requests.post")
    def test_grobid_service_unavailable(self, mock_post, sample_pdf_path):
        """Test Grobid service unavailable."""
        from packages.ingestion.grobid_parser import parse_with_grobid

        # Mock 503 response
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_post.return_value = mock_response

        result = parse_with_grobid(sample_pdf_path)

        assert result is None

    @patch("packages.ingestion.grobid_parser.requests.post")
    def test_grobid_connection_error(self, mock_post, sample_pdf_path):
        """Test Grobid connection error."""
        from packages.ingestion.grobid_parser import parse_with_grobid
        import requests

        # Mock connection error
        mock_post.side_effect = requests.ConnectionError("Connection refused")

        result = parse_with_grobid(sample_pdf_path)

        assert result is None


class TestLatexExtractor:
    """Tests for LaTeX extraction from parsed content."""

    def test_extract_equations(self):
        """Test equation extraction from markdown."""
        from packages.ingestion.latex_extractor import extract_equations

        markdown = """
        Some text before
        $$H = \\sum_i X_i$$
        Some text after
        $E = mc^2$
        """

        equations = extract_equations(markdown)

        assert len(equations) >= 1
        assert any("H =" in eq or "E =" in eq for eq in equations)

    def test_extract_theorems(self):
        """Test theorem extraction."""
        from packages.ingestion.latex_extractor import extract_theorems

        text = """
        **Theorem 1** (Quantum Error Correction): 
        For any quantum code with distance d...
        
        **Lemma 2**: The minimum distance satisfies...
        """

        theorems = extract_theorems(text)

        assert len(theorems) >= 1
        assert any("Quantum Error Correction" in t for t in theorems)

    def test_extract_constants(self):
        """Test physics constant extraction."""
        from packages.ingestion.latex_extractor import extract_constants

        text = """
        The speed of light c = 3×10^8 m/s
        Planck constant h = 6.626×10^-34 J·s
        Gravitational constant G = 6.674×10^-11 m^3⋅kg^-1⋅s^-2
        """

        constants = extract_constants(text)

        assert len(constants) >= 1
        # Should find at least one known constant
        constant_names = [c.lower() for c in constants]
        assert any(name in ["c", "h", "g", "planck", "gravitational"] 
                   for name in constant_names)

    def test_extract_empty_content(self):
        """Test extraction from empty content."""
        from packages.ingestion.latex_extractor import (
            extract_equations,
            extract_theorems,
            extract_constants
        )

        assert extract_equations("") == []
        assert extract_theorems("") == []
        assert extract_constants("") == []


class TestSemanticChunker:
    """Tests for semantic chunking by section."""

    def test_chunk_by_sections(self, sample_markdown):
        """Test chunking markdown into sections."""
        from packages.ingestion.semantic_chunker import chunk_by_sections

        chunks = chunk_by_sections(sample_markdown)

        assert len(chunks) > 0
        # Should have Abstract, Introduction, Methods, Results, Conclusion
        assert any(chunk["title"] == "Abstract" for chunk in chunks)
        assert any(chunk["title"] == "Introduction" for chunk in chunks)

    def test_chunk_with_metadata(self, sample_markdown):
        """Test chunks include metadata."""
        from packages.ingestion.semantic_chunker import chunk_by_sections

        chunks = chunk_by_sections(sample_markdown)

        for chunk in chunks:
            assert "title" in chunk
            assert "content" in chunk
            assert "level" in chunk
            assert isinstance(chunk["level"], int)

    def test_chunk_empty_content(self):
        """Test chunking empty content."""
        from packages.ingestion.semantic_chunker import chunk_by_sections

        chunks = chunk_by_sections("")

        assert chunks == []

    def test_chunk_nested_sections(self):
        """Test chunking with nested sections."""
        from packages.ingestion.semantic_chunker import chunk_by_sections

        markdown = """
# Main Title

## Section 1
Content 1

### Subsection 1.1
Subcontent 1.1

## Section 2
Content 2
"""

        chunks = chunk_by_sections(markdown)

        # Should handle nested structure
        assert len(chunks) >= 3
        levels = [chunk["level"] for chunk in chunks]
        assert 1 in levels  # Main title
        assert 2 in levels  # Sections
        assert 3 in levels  # Subsections


class TestParsingPipeline:
    """Tests for the complete parsing pipeline."""

    @patch("packages.ingestion.parsing_pipeline.parse_with_marker")
    @patch("packages.ingestion.parsing_pipeline.parse_with_grobid")
    def test_pipeline_marker_success(
        self, mock_grobid, mock_marker, sample_pdf_path, sample_markdown, sample_grobid_xml
    ):
        """Test pipeline with successful Marker parsing."""
        from packages.ingestion.parsing_pipeline import parse_pdf

        mock_marker.return_value = sample_markdown
        mock_grobid.return_value = sample_grobid_xml

        result = parse_pdf(sample_pdf_path)

        assert result is not None
        assert isinstance(result, ParsedPaper)
        assert result.parser_used == ParserType.MARKER
        assert "Quantum Error Correction" in result.title
        mock_marker.assert_called_once()
        mock_grobid.assert_called_once()

    @patch("packages.ingestion.parsing_pipeline.parse_with_marker")
    @patch("packages.ingestion.parsing_pipeline.parse_with_pymupdf")
    @patch("packages.ingestion.parsing_pipeline.parse_with_grobid")
    def test_pipeline_fallback_to_pymupdf(
        self, mock_grobid, mock_pymupdf, mock_marker, sample_pdf_path, sample_grobid_xml
    ):
        """Test pipeline falls back to PyMuPDF when Marker fails."""
        from packages.ingestion.parsing_pipeline import parse_pdf

        mock_marker.return_value = None  # Marker fails
        mock_pymupdf.return_value = "Simple text content"
        mock_grobid.return_value = sample_grobid_xml

        result = parse_pdf(sample_pdf_path)

        assert result is not None
        assert result.parser_used == ParserType.PYMUPDF
        mock_marker.assert_called_once()
        mock_pymupdf.assert_called_once()

    @patch("packages.ingestion.parsing_pipeline.parse_with_marker")
    @patch("packages.ingestion.parsing_pipeline.parse_with_pymupdf")
    @patch("packages.ingestion.parsing_pipeline.parse_with_grobid")
    def test_pipeline_all_parsers_fail(
        self, mock_grobid, mock_pymupdf, mock_marker, sample_pdf_path
    ):
        """Test pipeline when all parsers fail."""
        from packages.ingestion.parsing_pipeline import parse_pdf

        mock_marker.return_value = None
        mock_pymupdf.return_value = None
        mock_grobid.return_value = None

        result = parse_pdf(sample_pdf_path)

        assert result is None

    @patch("packages.ingestion.parsing_pipeline.parse_with_marker")
    @patch("packages.ingestion.parsing_pipeline.parse_with_grobid")
    @patch("packages.ingestion.parsing_pipeline.extract_equations")
    @patch("packages.ingestion.parsing_pipeline.extract_theorems")
    def test_pipeline_latex_extraction(
        self,
        mock_theorems,
        mock_equations,
        mock_grobid,
        mock_marker,
        sample_pdf_path,
        sample_markdown,
    ):
        """Test pipeline extracts LaTeX content."""
        from packages.ingestion.parsing_pipeline import parse_pdf

        mock_marker.return_value = sample_markdown
        mock_grobid.return_value = None
        mock_equations.return_value = ["$E=mc^2$"]
        mock_theorems.return_value = ["Theorem 1: Test theorem"]

        result = parse_pdf(sample_pdf_path)

        assert result is not None
        mock_equations.assert_called()
        mock_theorems.assert_called()


class TestParsingQualityMetrics:
    """Tests for parsing quality assessment."""

    def test_validate_parsed_paper(self):
        """Test validation of parsed paper structure."""
        from packages.ingestion.parsing_pipeline import validate_parsed_paper

        valid_paper = ParsedPaper(
            arxiv_id="2401.12345",
            title="Test Paper",
            abstract="Test abstract with sufficient length for validation",
            authors=["Author One", "Author Two"],
            categories=["quant-ph"],
            primary_category="quant-ph",
            published_date="2024-01-23",
            full_text="Full text content" * 100,  # Sufficient length
            sections=[],
            citations=[],
            concepts=[],
            parser_used=ParserType.MARKER,
        )

        is_valid, issues = validate_parsed_paper(valid_paper)

        assert is_valid
        assert len(issues) == 0

    def test_validate_insufficient_content(self):
        """Test validation catches insufficient content."""
        from packages.ingestion.parsing_pipeline import validate_parsed_paper

        invalid_paper = ParsedPaper(
            arxiv_id="2401.12345",
            title="Test",
            abstract="Short",
            authors=[],
            categories=["quant-ph"],
            primary_category="quant-ph",
            published_date="2024-01-23",
            full_text="Too short",
            sections=[],
            citations=[],
            concepts=[],
            parser_used=ParserType.MARKER,
        )

        is_valid, issues = validate_parsed_paper(invalid_paper)

        assert not is_valid
        assert len(issues) > 0


class TestErrorHandling:
    """Tests for error handling in parsing pipeline."""

    def test_handle_corrupted_pdf(self, tmp_path):
        """Test handling of corrupted PDF files."""
        from packages.ingestion.parsing_pipeline import parse_pdf

        corrupted_pdf = tmp_path / "corrupted.pdf"
        corrupted_pdf.write_bytes(b"Not a valid PDF")

        with patch("packages.ingestion.parsing_pipeline.parse_with_marker") as mock:
            mock.side_effect = Exception("Corrupted file")
            result = parse_pdf(corrupted_pdf)

        # Should handle error gracefully
        assert result is None or isinstance(result, ParsedPaper)

    def test_handle_missing_file(self):
        """Test handling of missing PDF file."""
        from packages.ingestion.parsing_pipeline import parse_pdf

        missing_file = Path("/nonexistent/file.pdf")
        result = parse_pdf(missing_file)

        assert result is None

    @patch("packages.ingestion.parsing_pipeline.parse_with_marker")
    def test_handle_parser_exception(self, mock_marker, sample_pdf_path):
        """Test handling of parser exceptions."""
        from packages.ingestion.parsing_pipeline import parse_pdf

        mock_marker.side_effect = RuntimeError("Parser crashed")

        # Should not raise, should return None or fallback
        result = parse_pdf(sample_pdf_path)

        assert result is None or isinstance(result, ParsedPaper)
