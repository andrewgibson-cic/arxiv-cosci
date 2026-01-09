"""Marker-based PDF parser for LaTeX-heavy papers.

Marker is optimized for converting PDFs to Markdown while preserving:
- LaTeX equations
- Complex layouts
- Tables and figures
- Section structure
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from packages.ingestion.models import (
    ArxivPaper,
    ParsedPaper,
    ParserType,
    Section,
)

logger = structlog.get_logger()


class MarkerConfig:
    """Configuration for Marker PDF parser."""

    def __init__(
        self,
        *,
        max_pages: int = 100,
        extract_images: bool = True,
        preserve_latex: bool = True,
        output_format: str = "markdown",
        langs: list[str] | None = None,
    ):
        """Initialize Marker configuration.

        Args:
            max_pages: Maximum pages to process (prevent hanging on huge PDFs)
            extract_images: Whether to extract and save images
            preserve_latex: Preserve LaTeX equations (critical for physics/math)
            output_format: Output format (markdown, json, etc.)
            langs: Language hints for OCR (default: ["en"])
        """
        self.max_pages = max_pages
        self.extract_images = extract_images
        self.preserve_latex = preserve_latex
        self.output_format = output_format
        self.langs = langs or ["en"]


class MarkerParser:
    """PDF parser using Marker for high-quality extraction.

    Marker uses vision models to understand document structure
    and preserve LaTeX equations, making it ideal for physics/math papers.
    """

    def __init__(self, config: MarkerConfig | None = None):
        """Initialize Marker parser.

        Args:
            config: Parser configuration
        """
        self.config = config or MarkerConfig()
        self.parser_type = ParserType.MARKER
        self._check_marker_available()

    def _check_marker_available(self) -> None:
        """Check if Marker is available."""
        try:
            import marker  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "Marker not installed. Install with: poetry install --with parsing"
            ) from e

    def extract_markdown(self, pdf_path: Path) -> tuple[str, dict[str, Any]]:
        """Extract markdown from PDF using Marker.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Tuple of (markdown_text, metadata_dict)

        Raises:
            FileNotFoundError: If PDF doesn't exist
            RuntimeError: If parsing fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info("parsing_with_marker", pdf_path=str(pdf_path))

        try:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict

            # Create models (cached on first run)
            model_dict = create_model_dict()

            # Convert PDF
            converter = PdfConverter(
                artifact_dict=model_dict,
                config={
                    "languages": self.config.langs,
                    "max_pages": self.config.max_pages,
                },
            )

            rendered = converter(str(pdf_path))

            # Extract markdown and metadata
            markdown_text = rendered.markdown
            metadata = {
                "pages": len(rendered.pages),
                "images": len(rendered.images) if self.config.extract_images else 0,
                "languages": rendered.languages,
            }

            logger.info(
                "marker_parse_complete",
                pages=metadata["pages"],
                markdown_length=len(markdown_text),
            )

            return markdown_text, metadata

        except Exception as e:
            logger.error("marker_parse_failed", error=str(e), pdf_path=str(pdf_path))
            raise RuntimeError(f"Marker parsing failed: {e}") from e

    def _extract_sections_from_markdown(self, markdown: str) -> list[Section]:
        """Extract sections from Marker's markdown output.

        Marker outputs well-structured markdown with headers.

        Args:
            markdown: Markdown text from Marker

        Returns:
            List of sections
        """
        sections: list[Section] = []
        lines = markdown.split("\n")

        current_section: str | None = None
        current_level = 1
        current_content: list[str] = []

        for line in lines:
            # Check for markdown headers
            if line.startswith("#"):
                # Save previous section
                if current_section:
                    sections.append(
                        Section(
                            title=current_section,
                            content="\n".join(current_content).strip(),
                            level=current_level,
                        )
                    )

                # Start new section
                level = len(line) - len(line.lstrip("#"))
                current_level = min(level, 6)  # Max level 6
                current_section = line.lstrip("#").strip()
                current_content = []
            else:
                current_content.append(line)

        # Don't forget last section
        if current_section:
            sections.append(
                Section(
                    title=current_section,
                    content="\n".join(current_content).strip(),
                    level=current_level,
                )
            )

        return sections

    def _extract_equations_from_markdown(self, markdown: str) -> list[str]:
        """Extract LaTeX equations from Marker markdown.

        Marker preserves equations in LaTeX format.

        Args:
            markdown: Markdown text

        Returns:
            List of equation strings
        """
        import re

        equations: list[str] = []

        # Display equations: $$...$$
        display_pattern = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
        for match in display_pattern.finditer(markdown):
            eq = match.group(1).strip()
            if eq and len(eq) > 2:
                equations.append(eq)

        # Inline equations: $...$
        inline_pattern = re.compile(r"\$(.+?)\$")
        for match in inline_pattern.finditer(markdown):
            eq = match.group(1).strip()
            # Filter out short matches that might be false positives
            if eq and len(eq) > 3 and not eq.isdigit():
                equations.append(eq)

        return list(set(equations))  # Deduplicate

    def parse(self, paper: ArxivPaper, output_dir: Path | None = None) -> ParsedPaper:
        """Parse paper with Marker.

        Args:
            paper: ArxivPaper with pdf_path
            output_dir: Optional directory to save markdown output

        Returns:
            ParsedPaper with extracted content

        Raises:
            ValueError: If PDF path not available
            RuntimeError: If parsing fails
        """
        if not paper.pdf_path or not paper.pdf_path.exists():
            raise ValueError(f"No PDF available for {paper.arxiv_id}")

        logger.info("parsing_paper_with_marker", arxiv_id=paper.arxiv_id)

        # Extract markdown
        markdown, metadata = self.extract_markdown(paper.pdf_path)

        # Save markdown if output directory provided
        markdown_path: Path | None = None
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            markdown_path = output_dir / f"{paper.arxiv_id.replace('/', '_')}_marker.md"
            markdown_path.write_text(markdown, encoding="utf-8")
            logger.debug("saved_markdown", path=str(markdown_path))

        # Extract structured content
        sections = self._extract_sections_from_markdown(markdown)
        equations = self._extract_equations_from_markdown(markdown)

        # Add equations to sections
        for section in sections:
            section.equations = self._extract_equations_from_markdown(section.content)

        # Calculate confidence based on metadata
        confidence = 0.95  # Marker is high quality
        if metadata.get("pages", 0) > self.config.max_pages:
            confidence = 0.85  # Truncated document

        return ParsedPaper(
            arxiv_id=paper.arxiv_id,
            title=paper.metadata.title,
            abstract=paper.metadata.abstract,
            authors=paper.metadata.author_list,
            categories=paper.metadata.category_list,
            full_text=markdown,
            sections=sections,
            equations=equations,
            parser_used=self.parser_type,
            parse_confidence=confidence,
            parsed_at=datetime.now(),
            pdf_path=paper.pdf_path,
            markdown_path=markdown_path,
        )


def parse_with_marker(
    paper: ArxivPaper,
    output_dir: Path | None = None,
    config: MarkerConfig | None = None,
) -> ParsedPaper:
    """Convenience function to parse paper with Marker.

    Args:
        paper: ArxivPaper with pdf_path
        output_dir: Optional directory to save markdown output
        config: Optional parser configuration

    Returns:
        ParsedPaper with extracted content
    """
    parser = MarkerParser(config)
    return parser.parse(paper, output_dir)