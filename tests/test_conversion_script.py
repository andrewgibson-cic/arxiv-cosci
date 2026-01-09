"""Tests for S2 metadata to ParsedPaper conversion."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from packages.ingestion.models import ParsedPaper, ParserType


def test_parsed_paper_creation():
    """Test creating a ParsedPaper from S2 metadata."""
    paper = ParsedPaper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Alice", "Bob"],
        abstract="This is a test abstract.",
        categories=["cs.AI", "cs.LG"],
        published_date=datetime.now(),
        full_text="",
        sections=[],
        citations=[],
        equations=[],
        parser_used=ParserType.PYMUPDF,
        parse_confidence=0.5,
    )
    
    assert paper.arxiv_id == "2401.12345"
    assert len(paper.authors) == 2
    assert paper.parser_used == ParserType.PYMUPDF
    assert paper.parse_confidence == 0.5


def test_parsed_paper_serialization():
    """Test ParsedPaper JSON serialization."""
    paper = ParsedPaper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Alice"],
        abstract="Test abstract",
        categories=["cs.AI"],
        published_date=datetime(2024, 1, 1),
        full_text="Test content",
        parser_used=ParserType.MARKER,
        parse_confidence=0.9,
    )
    
    # Serialize to JSON
    json_str = paper.model_dump_json()
    assert "2401.12345" in json_str
    assert "Test Paper" in json_str
    
    # Deserialize back
    loaded = ParsedPaper.model_validate_json(json_str)
    assert loaded.arxiv_id == paper.arxiv_id
    assert loaded.title == paper.title
    assert loaded.parser_used == paper.parser_used


def test_parsed_paper_with_empty_fields():
    """Test ParsedPaper with minimal required fields."""
    paper = ParsedPaper(
        arxiv_id="2401.00000",
        title="Minimal Paper",
        authors=[],
        abstract="",
        categories=[],
    )
    
    assert paper.arxiv_id == "2401.00000"
    assert paper.authors == []
    assert paper.abstract == ""
    assert paper.full_text == ""
    assert paper.sections == []
    assert paper.citations == []
    assert paper.equations == []
    assert paper.parser_used == ParserType.PYMUPDF  # Default
    assert paper.parse_confidence == 1.0  # Default


def test_parser_type_enum():
    """Test ParserType enum values."""
    assert ParserType.PYMUPDF.value == "pymupdf"
    assert ParserType.MARKER.value == "marker"
    assert ParserType.GROBID.value == "grobid"
    assert ParserType.NOUGAT.value == "nougat"


@pytest.mark.asyncio
async def test_conversion_workflow():
    """Test the full conversion workflow."""
    # Sample S2 metadata
    s2_data = {
        "id": "2401.12345",
        "authors": "Alice Smith, Bob Jones",
        "title": "Test Paper Title",
        "abstract": "This is a test abstract with content.",
        "categories": "cs.AI, cs.LG",
        "update_date": "2024",
    }
    
    # Convert to ParsedPaper
    paper = ParsedPaper(
        arxiv_id=s2_data["id"],
        title=s2_data["title"],
        authors=s2_data["authors"].split(", ") if s2_data["authors"] else [],
        abstract=s2_data["abstract"] or "",
        categories=[cat.strip() for cat in s2_data.get("categories", "").split(",") if cat.strip()],
        published_date=datetime.now(),
        full_text="",
        sections=[],
        citations=[],
        equations=[],
        parser_used=ParserType.PYMUPDF,
        parse_confidence=0.5,
    )
    
    # Validate conversion
    assert paper.arxiv_id == "2401.12345"
    assert len(paper.authors) == 2
    assert paper.authors[0] == "Alice Smith"
    assert paper.authors[1] == "Bob Jones"
    assert len(paper.categories) == 2
    assert "cs.AI" in paper.categories
    assert "cs.LG" in paper.categories
    assert paper.title == "Test Paper Title"
    assert "test abstract" in paper.abstract.lower()