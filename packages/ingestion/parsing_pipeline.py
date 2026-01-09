"""Comprehensive parsing pipeline orchestrating all parsers.

Combines Marker, Grobid, PyMuPDF, and LaTeX extraction to create
a complete ParsedPaper with maximum information extraction.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from packages.ingestion.grobid_parser import GrobidConfig, GrobidParser
from packages.ingestion.latex_extractor import LaTeXExtractor
from packages.ingestion.marker_parser import MarkerConfig, MarkerParser
from packages.ingestion.models import ArxivPaper, Citation, ParsedPaper, ParserType, Section
from packages.ingestion.semantic_chunker import PaperChunk, SemanticChunker
from packages.ingestion.text_extractor import PyMuPDFExtractor

logger = structlog.get_logger()


@dataclass
class ParsingQuality:
    """Quality metrics for parsed paper."""

    arxiv_id: str
    marker_success: bool
    grobid_success: bool
    pymupdf_fallback: bool
    section_count: int
    equation_count: int
    citation_count: int
    reference_count: int
    parse_time_seconds: float
    warnings: list[str]
    errors: list[str]


class ParsingPipelineConfig:
    """Configuration for parsing pipeline."""

    def __init__(
        self,
        *,
        use_marker: bool = True,
        use_grobid: bool = True,
        use_pymupdf_fallback: bool = True,
        marker_config: MarkerConfig | None = None,
        grobid_config: GrobidConfig | None = None,
        output_dir: Path | None = None,
        extract_latex: bool = True,
        create_chunks: bool = True,
        max_chunk_size: int = 2000,
    ):
        """Initialize pipeline configuration.

        Args:
            use_marker: Use Marker for high-quality parsing
            use_grobid: Use Grobid for citation extraction
            use_pymupdf_fallback: Fall back to PyMuPDF if others fail
            marker_config: Marker configuration
            grobid_config: Grobid configuration
            output_dir: Directory to save intermediate outputs
            extract_latex: Extract LaTeX entities
            create_chunks: Create semantic chunks
            max_chunk_size: Maximum chunk size in characters
        """
        self.use_marker = use_marker
        self.use_grobid = use_grobid
        self.use_pymupdf_fallback = use_pymupdf_fallback
        self.marker_config = marker_config or MarkerConfig()
        self.grobid_config = grobid_config or GrobidConfig()
        self.output_dir = output_dir
        self.extract_latex = extract_latex
        self.create_chunks = create_chunks
        self.max_chunk_size = max_chunk_size


class ParsingPipeline:
    """Comprehensive parsing pipeline."""

    def __init__(self, config: ParsingPipelineConfig | None = None):
        """Initialize parsing pipeline.

        Args:
            config: Pipeline configuration
        """
        self.config = config or ParsingPipelineConfig()
        self.marker_parser: MarkerParser | None = None
        self.grobid_parser: GrobidParser | None = None
        self.pymupdf_extractor = PyMuPDFExtractor()
        self.latex_extractor = LaTeXExtractor()
        self.chunker = SemanticChunker(max_chunk_size=self.config.max_chunk_size)

        # Initialize parsers based on config
        if self.config.use_marker:
            try:
                self.marker_parser = MarkerParser(self.config.marker_config)
            except ImportError:
                logger.warning("marker_not_available", fallback="pymupdf")
                self.marker_parser = None

        if self.config.use_grobid:
            self.grobid_parser = GrobidParser(self.config.grobid_config)

    async def close(self) -> None:
        """Close async resources."""
        if self.grobid_parser:
            await self.grobid_parser.close()

    async def parse(self, paper: ArxivPaper) -> tuple[ParsedPaper, ParsingQuality]:
        """Parse paper using all available methods.

        Args:
            paper: ArxivPaper with pdf_path

        Returns:
            Tuple of (parsed_paper, quality_metrics)

        Raises:
            ValueError: If no PDF available
            RuntimeError: If all parsing methods fail
        """
        if not paper.pdf_path or not paper.pdf_path.exists():
            raise ValueError(f"No PDF available for {paper.arxiv_id}")

        start_time = datetime.now()
        warnings: list[str] = []
        errors: list[str] = []

        logger.info("starting_parse_pipeline", arxiv_id=paper.arxiv_id)

        # Initialize result tracking
        marker_success = False
        grobid_success = False
        pymupdf_fallback = False
        parsed_paper: ParsedPaper | None = None
        grobid_data: dict[str, Any] | None = None

        # Step 1: Try Marker for high-quality full-text extraction
        if self.config.use_marker and self.marker_parser:
            try:
                logger.info("attempting_marker_parse", arxiv_id=paper.arxiv_id)
                parsed_paper = self.marker_parser.parse(paper, self.config.output_dir)
                marker_success = True
                logger.info("marker_parse_success", arxiv_id=paper.arxiv_id)
            except Exception as e:
                logger.error("marker_parse_failed", arxiv_id=paper.arxiv_id, error=str(e))
                errors.append(f"Marker failed: {e}")
                parsed_paper = None

        # Step 2: Fall back to PyMuPDF if Marker failed or not available
        if not parsed_paper and self.config.use_pymupdf_fallback:
            try:
                logger.info("attempting_pymupdf_parse", arxiv_id=paper.arxiv_id)
                parsed_paper = self.pymupdf_extractor.parse(paper)
                pymupdf_fallback = True
                warnings.append("Using PyMuPDF fallback (lower quality)")
                logger.info("pymupdf_parse_success", arxiv_id=paper.arxiv_id)
            except Exception as e:
                logger.error("pymupdf_parse_failed", arxiv_id=paper.arxiv_id, error=str(e))
                errors.append(f"PyMuPDF failed: {e}")

        if not parsed_paper:
            raise RuntimeError(f"All parsing methods failed for {paper.arxiv_id}")

        # Step 3: Try Grobid for citation extraction (parallel with Marker/PyMuPDF)
        if self.config.use_grobid and self.grobid_parser:
            try:
                logger.info("attempting_grobid_parse", arxiv_id=paper.arxiv_id)
                _, grobid_data = await self.grobid_parser.parse(paper, self.config.output_dir)
                grobid_success = True
                logger.info("grobid_parse_success", arxiv_id=paper.arxiv_id)

                # Merge Grobid citations with parsed paper
                if grobid_data and "citations" in grobid_data:
                    parsed_paper.citations.extend(grobid_data["citations"])
                    # Deduplicate citations
                    seen = set()
                    unique_citations = []
                    for cit in parsed_paper.citations:
                        key = (cit.arxiv_id, cit.doi, cit.raw_text[:50])
                        if key not in seen:
                            seen.add(key)
                            unique_citations.append(cit)
                    parsed_paper.citations = unique_citations

            except Exception as e:
                logger.warning("grobid_parse_failed", arxiv_id=paper.arxiv_id, error=str(e))
                warnings.append(f"Grobid failed: {e}")

        # Step 4: Extract LaTeX entities if requested
        if self.config.extract_latex:
            try:
                logger.info("extracting_latex_entities", arxiv_id=paper.arxiv_id)
                math_entities = self.latex_extractor.extract_all(parsed_paper.full_text)

                # Add equations from LaTeX extractor to parsed paper
                if "display_equations" in math_entities:
                    for entity in math_entities["display_equations"]:
                        if entity.content not in parsed_paper.equations:
                            parsed_paper.equations.append(entity.content)

                logger.debug(
                    "latex_extraction_complete",
                    equations=len(math_entities.get("display_equations", [])),
                    theorems=len(math_entities.get("theorems", [])),
                )
            except Exception as e:
                logger.warning("latex_extraction_failed", arxiv_id=paper.arxiv_id, error=str(e))
                warnings.append(f"LaTeX extraction incomplete: {e}")

        # Calculate parsing time
        parse_time = (datetime.now() - start_time).total_seconds()

        # Create quality metrics
        quality = ParsingQuality(
            arxiv_id=paper.arxiv_id,
            marker_success=marker_success,
            grobid_success=grobid_success,
            pymupdf_fallback=pymupdf_fallback,
            section_count=len(parsed_paper.sections),
            equation_count=len(parsed_paper.equations),
            citation_count=len(parsed_paper.citations),
            reference_count=0,  # Could extract from Grobid
            parse_time_seconds=parse_time,
            warnings=warnings,
            errors=errors,
        )

        logger.info(
            "parse_pipeline_complete",
            arxiv_id=paper.arxiv_id,
            quality=marker_success and not pymupdf_fallback,
            parse_time=parse_time,
            sections=quality.section_count,
            equations=quality.equation_count,
            citations=quality.citation_count,
        )

        return parsed_paper, quality

    def create_chunks(self, parsed_paper: ParsedPaper) -> list[PaperChunk]:
        """Create semantic chunks from parsed paper.

        Args:
            parsed_paper: Parsed paper

        Returns:
            List of paper chunks
        """
        if not self.config.create_chunks:
            return []

        return self.chunker.chunk_paper(parsed_paper)


async def parse_paper_full(
    paper: ArxivPaper,
    config: ParsingPipelineConfig | None = None,
) -> tuple[ParsedPaper, ParsingQuality, list[PaperChunk]]:
    """Convenience function to fully parse a paper.

    Args:
        paper: ArxivPaper with pdf_path
        config: Optional pipeline configuration

    Returns:
        Tuple of (parsed_paper, quality_metrics, chunks)
    """
    pipeline = ParsingPipeline(config)
    try:
        parsed_paper, quality = await pipeline.parse(paper)
        chunks = pipeline.create_chunks(parsed_paper) if config and config.create_chunks else []
        return parsed_paper, quality, chunks
    finally:
        await pipeline.close()


async def parse_batch(
    papers: list[ArxivPaper],
    config: ParsingPipelineConfig | None = None,
    *,
    skip_errors: bool = True,
) -> list[tuple[ParsedPaper, ParsingQuality]]:
    """Parse multiple papers sequentially.

    Args:
        papers: List of papers to parse
        config: Optional pipeline configuration
        skip_errors: Continue on individual failures

    Returns:
        List of (parsed_paper, quality) tuples
    """
    pipeline = ParsingPipeline(config)
    results: list[tuple[ParsedPaper, ParsingQuality]] = []

    try:
        for i, paper in enumerate(papers):
            try:
                parsed_paper, quality = await pipeline.parse(paper)
                results.append((parsed_paper, quality))

                if (i + 1) % 10 == 0:
                    logger.info("batch_parse_progress", completed=i + 1, total=len(papers))

            except Exception as e:
                logger.error("batch_parse_failed", arxiv_id=paper.arxiv_id, error=str(e))
                if not skip_errors:
                    raise

        return results
    finally:
        await pipeline.close()