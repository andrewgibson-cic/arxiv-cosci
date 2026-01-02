"""Text extraction from PDF files.

This module provides a fallback chain of PDF extractors:
1. PyMuPDF - Fast baseline extraction
2. (Future) Marker - Better handling of complex layouts
3. (Future) Nougat - Vision-based for heavy LaTeX

Currently implements PyMuPDF as the baseline extractor.
"""

import re
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF
import structlog

from packages.ingestion.models import (
    ArxivPaper,
    Citation,
    PaperMetadata,
    ParsedPaper,
    ParserType,
    Section,
)

logger = structlog.get_logger()

# Regex patterns for section detection
SECTION_PATTERNS = [
    # Numbered sections: "1. Introduction", "2.1 Methods"
    re.compile(r"^(\d+\.?\d*\.?\d*)\s+(.+)$", re.MULTILINE),
    # Unnumbered common sections
    re.compile(
        r"^(Abstract|Introduction|Background|Methods?|Results?|Discussion|"
        r"Conclusions?|References|Acknowledgments?|Appendix)\s*$",
        re.MULTILINE | re.IGNORECASE,
    ),
]

# arXiv ID pattern for citation detection
ARXIV_ID_PATTERN = re.compile(
    r"(?:arXiv:|arxiv:)?\s*(\d{4}\.\d{4,5}(?:v\d+)?)|"  # New format: 2401.12345
    r"(?:arXiv:|arxiv:)?\s*([a-z-]+/\d{7})",  # Old format: hep-th/9901001
    re.IGNORECASE,
)

# DOI pattern
DOI_PATTERN = re.compile(r"10\.\d{4,}/[^\s]+")

# LaTeX equation patterns
EQUATION_PATTERNS = [
    re.compile(r"\$\$([^$]+)\$\$"),  # Display math
    re.compile(r"\$([^$]+)\$"),  # Inline math
    re.compile(r"\\begin\{equation\}(.+?)\\end\{equation\}", re.DOTALL),
    re.compile(r"\\begin\{align\}(.+?)\\end\{align\}", re.DOTALL),
]


class PyMuPDFExtractor:
    """Text extraction using PyMuPDF (fitz).

    Fast and reliable for basic text extraction.
    Limited handling of complex layouts and equations.
    """

    def __init__(self) -> None:
        self.parser_type = ParserType.PYMUPDF

    def extract_text(self, pdf_path: Path) -> str:
        """Extract raw text from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text content
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        text_parts: list[str] = []

        with fitz.open(pdf_path) as doc:
            for page in doc:
                # Extract text with layout preservation
                text = page.get_text("text")
                text_parts.append(text)

        return "\n\n".join(text_parts)

    def extract_sections(self, text: str) -> list[Section]:
        """Attempt to identify document sections.

        Args:
            text: Full document text

        Returns:
            List of detected sections
        """
        sections: list[Section] = []
        current_section: str | None = None
        current_content: list[str] = []
        current_level = 1

        lines = text.split("\n")

        for line in lines:
            stripped = line.strip()
            is_header = False

            # Check numbered section patterns
            match = SECTION_PATTERNS[0].match(stripped)
            if match:
                # Save previous section
                if current_section:
                    sections.append(
                        Section(
                            title=current_section,
                            content="\n".join(current_content).strip(),
                            level=current_level,
                        )
                    )

                number = match.group(1)
                current_section = match.group(2)
                current_level = number.count(".") + 1
                current_content = []
                is_header = True

            # Check unnumbered section patterns
            if not is_header:
                match = SECTION_PATTERNS[1].match(stripped)
                if match:
                    if current_section:
                        sections.append(
                            Section(
                                title=current_section,
                                content="\n".join(current_content).strip(),
                                level=current_level,
                            )
                        )
                    current_section = match.group(1)
                    current_level = 1
                    current_content = []
                    is_header = True

            if not is_header:
                current_content.append(line)

        # Don't forget the last section
        if current_section:
            sections.append(
                Section(
                    title=current_section,
                    content="\n".join(current_content).strip(),
                    level=current_level,
                )
            )

        return sections

    def extract_citations(self, text: str) -> list[Citation]:
        """Extract citation references from text.

        Args:
            text: Document text

        Returns:
            List of detected citations
        """
        citations: list[Citation] = []
        seen_ids: set[str] = set()

        # Find arXiv IDs
        for match in ARXIV_ID_PATTERN.finditer(text):
            arxiv_id = match.group(1) or match.group(2)
            if arxiv_id and arxiv_id not in seen_ids:
                seen_ids.add(arxiv_id)

                # Get surrounding context (±100 chars)
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end].replace("\n", " ").strip()

                citations.append(
                    Citation(
                        raw_text=match.group(0),
                        arxiv_id=arxiv_id,
                        context=context,
                    )
                )

        # Find DOIs
        for match in DOI_PATTERN.finditer(text):
            doi = match.group(0)
            if doi not in seen_ids:
                seen_ids.add(doi)

                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end].replace("\n", " ").strip()

                citations.append(
                    Citation(
                        raw_text=doi,
                        doi=doi,
                        context=context,
                    )
                )

        return citations

    def extract_equations(self, text: str) -> list[str]:
        """Extract LaTeX equations from text.

        Note: PyMuPDF doesn't preserve LaTeX well; this catches
        any that remain in the extracted text.

        Args:
            text: Document text

        Returns:
            List of equation strings
        """
        equations: list[str] = []

        for pattern in EQUATION_PATTERNS:
            for match in pattern.finditer(text):
                eq = match.group(1).strip()
                if eq and len(eq) > 3:  # Filter trivial matches
                    equations.append(eq)

        return equations

    def parse(self, paper: ArxivPaper) -> ParsedPaper:
        """Fully parse a downloaded paper.

        Args:
            paper: ArxivPaper with pdf_path

        Returns:
            ParsedPaper with extracted content
        """
        if not paper.pdf_path or not paper.pdf_path.exists():
            raise ValueError(f"No PDF available for {paper.arxiv_id}")

        logger.info("parsing_pdf", arxiv_id=paper.arxiv_id, parser="pymupdf")

        full_text = self.extract_text(paper.pdf_path)
        sections = self.extract_sections(full_text)
        citations = self.extract_citations(full_text)
        equations = self.extract_equations(full_text)

        # Add equations found in sections
        for section in sections:
            section.equations = self.extract_equations(section.content)

        return ParsedPaper(
            arxiv_id=paper.arxiv_id,
            title=paper.metadata.title,
            abstract=paper.metadata.abstract,
            authors=paper.metadata.author_list,
            categories=paper.metadata.category_list,
            full_text=full_text,
            sections=sections,
            citations=citations,
            equations=equations,
            parser_used=self.parser_type,
            parse_confidence=0.7,  # PyMuPDF is baseline confidence
            parsed_at=datetime.now(),
            pdf_path=paper.pdf_path,
        )


def parse_paper(paper: ArxivPaper) -> ParsedPaper:
    """Parse a paper using the best available extractor.

    Currently uses PyMuPDF. Future versions will implement
    fallback chain with Nougat and Marker.

    Args:
        paper: ArxivPaper with pdf_path

    Returns:
        ParsedPaper with extracted content
    """
    extractor = PyMuPDFExtractor()
    return extractor.parse(paper)


def parse_pdf_file(
    pdf_path: Path,
    metadata: PaperMetadata | None = None,
) -> ParsedPaper:
    """Parse a PDF file directly.

    Convenience function for testing or standalone use.

    Args:
        pdf_path: Path to PDF file
        metadata: Optional metadata (will use placeholders if not provided)

    Returns:
        ParsedPaper with extracted content
    """
    if metadata is None:
        # Create placeholder metadata from filename
        arxiv_id = pdf_path.stem.replace("_", "/")
        metadata = PaperMetadata(
            id=arxiv_id,
            title="Unknown",
            authors="Unknown",
            categories="unknown",
            abstract="",
            update_date=datetime.now().isoformat(),
        )

    paper = ArxivPaper(
        metadata=metadata,
        pdf_path=pdf_path,
        downloaded_at=datetime.now(),
    )

    return parse_paper(paper)
