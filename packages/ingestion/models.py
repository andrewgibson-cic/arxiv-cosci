"""Pydantic models for ArXiv paper data.

These models represent papers at different stages of processing:
- PaperMetadata: Raw metadata from Kaggle/arXiv API
- ArxivPaper: Full paper with PDF path
- ParsedPaper: Paper with extracted text and sections
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ArxivCategory(str, Enum):
    """Primary arXiv categories for physics and mathematics."""

    # High-Energy Physics
    HEP_TH = "hep-th"
    HEP_PH = "hep-ph"
    HEP_LAT = "hep-lat"
    HEP_EX = "hep-ex"

    # General Relativity
    GR_QC = "gr-qc"

    # Quantum Physics
    QUANT_PH = "quant-ph"

    # Condensed Matter (selected)
    COND_MAT = "cond-mat"

    # Mathematics (selected)
    MATH_QA = "math.QA"
    MATH_MP = "math-ph"
    MATH_AG = "math.AG"
    MATH_DG = "math.DG"

    # Astrophysics
    ASTRO_PH = "astro-ph"

    # Nuclear
    NUCL_TH = "nucl-th"
    NUCL_EX = "nucl-ex"


class CitationIntent(str, Enum):
    """Classification of citation intent."""

    METHOD = "method"
    BACKGROUND = "background"
    RESULT = "result"
    CRITIQUE = "critique"
    EXTENSION = "extension"
    UNKNOWN = "unknown"


class ParserType(str, Enum):
    """PDF parser used for extraction."""

    NOUGAT = "nougat"
    MARKER = "marker"
    PYMUPDF = "pymupdf"
    GROBID = "grobid"


class PaperMetadata(BaseModel):
    """Raw metadata from Kaggle arXiv dataset.

    Matches the schema of arxiv-metadata-oai-snapshot.json
    """

    id: str = Field(..., description="ArXiv ID (e.g., '2401.12345')")
    submitter: str | None = None
    authors: str = Field(..., description="Raw author string")
    title: str
    comments: str | None = None
    journal_ref: str | None = Field(None, alias="journal-ref")
    doi: str | None = None
    report_no: str | None = Field(None, alias="report-no")
    categories: str = Field(..., description="Space-separated category list")
    license: str | None = None
    abstract: str
    versions: list[dict[str, Any]] = Field(default_factory=list)
    update_date: str
    authors_parsed: list[list[str]] = Field(default_factory=list)

    @field_validator("categories", mode="before")
    @classmethod
    def normalize_categories(cls, v: str) -> str:
        """Ensure categories are space-separated."""
        return v.replace(",", " ").strip()

    @property
    def primary_category(self) -> str:
        """Get the primary (first) category."""
        return self.categories.split()[0] if self.categories else ""

    @property
    def category_list(self) -> list[str]:
        """Get list of all categories."""
        return self.categories.split()

    @property
    def author_list(self) -> list[str]:
        """Get list of author names."""
        if self.authors_parsed:
            return [
                f"{parts[1]} {parts[0]}".strip()
                for parts in self.authors_parsed
                if parts
            ]
        return [a.strip() for a in self.authors.split(",")]

    @property
    def arxiv_url(self) -> str:
        """Get the arXiv abstract page URL."""
        return f"https://arxiv.org/abs/{self.id}"

    @property
    def pdf_url(self) -> str:
        """Get the PDF download URL."""
        return f"https://arxiv.org/pdf/{self.id}.pdf"


class ArxivPaper(BaseModel):
    """Paper with associated PDF file."""

    metadata: PaperMetadata
    pdf_path: Path | None = None
    downloaded_at: datetime | None = None

    @property
    def arxiv_id(self) -> str:
        """Convenience accessor for arXiv ID."""
        return self.metadata.id


class Section(BaseModel):
    """A section of a parsed paper."""

    title: str
    content: str
    level: int = Field(1, ge=1, le=6)
    equations: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    """A citation reference extracted from a paper."""

    raw_text: str
    arxiv_id: str | None = None
    doi: str | None = None
    context: str = Field("", description="Surrounding sentence")
    intent: CitationIntent = CitationIntent.UNKNOWN


class ParsedPaper(BaseModel):
    """Paper with fully extracted and structured content."""

    arxiv_id: str
    title: str
    abstract: str
    authors: list[str]
    categories: list[str]
    published_date: datetime | None = None

    # Parsed content
    full_text: str = ""
    sections: list[Section] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    equations: list[str] = Field(default_factory=list)

    # Parsing metadata
    parser_used: ParserType = ParserType.PYMUPDF
    parse_confidence: float = Field(1.0, ge=0.0, le=1.0)
    parsed_at: datetime = Field(default_factory=datetime.now)

    # File references
    pdf_path: Path | None = None
    markdown_path: Path | None = None

    @classmethod
    def from_metadata(cls, metadata: PaperMetadata) -> "ParsedPaper":
        """Create a ParsedPaper from metadata (before parsing)."""
        return cls(
            arxiv_id=metadata.id,
            title=metadata.title,
            abstract=metadata.abstract,
            authors=metadata.author_list,
            categories=metadata.category_list,
        )


class ConceptType(str, Enum):
    """Types of scientific concepts extracted from papers."""

    ALGORITHM = "algorithm"
    DATASET = "dataset"
    TASK = "task"
    METRIC = "metric"
    FRAMEWORK = "framework"
    THEOREM = "theorem"
    EQUATION = "equation"
    CONSTANT = "constant"
    METHOD = "method"
    CONJECTURE = "conjecture"


class Concept(BaseModel):
    """A scientific concept extracted from papers."""

    name: str
    concept_type: ConceptType
    description: str = ""
    paper_ids: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None

    @property
    def paper_count(self) -> int:
        """Number of papers mentioning this concept."""
        return len(self.paper_ids)
