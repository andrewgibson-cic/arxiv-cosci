"""Semantic chunking of scientific papers.

Splits papers into meaningful chunks while preserving:
- Section boundaries
- Equation context
- Citation context
- Paragraph coherence
"""

from dataclasses import dataclass
from typing import Any

import structlog

from packages.ingestion.models import ParsedPaper, Section

logger = structlog.get_logger()


@dataclass
class PaperChunk:
    """A semantic chunk of a paper."""

    arxiv_id: str
    section_type: str  # "abstract", "introduction", "methods", etc.
    title: str  # Section title
    content: str
    equations: list[str]  # LaTeX equations in this chunk
    citations: list[str]  # Citation IDs referenced
    position: int  # Order in paper (0-indexed)
    level: int  # Section level (1-6)
    word_count: int
    char_count: int
    embedding: list[float] | None = None
    metadata: dict[str, Any] | None = None


class SemanticChunker:
    """Chunker that respects document structure and semantics."""

    # Standard section types in scientific papers
    SECTION_TYPES = {
        "abstract": ["abstract", "summary"],
        "introduction": ["introduction", "intro", "background"],
        "methods": ["methods", "methodology", "approach", "materials and methods"],
        "theory": ["theory", "theoretical framework", "model"],
        "results": ["results", "findings", "experiments", "experimental results"],
        "discussion": ["discussion", "analysis"],
        "conclusion": ["conclusion", "conclusions", "summary", "future work"],
        "references": ["references", "bibliography", "citations"],
        "appendix": ["appendix", "supplementary"],
        "acknowledgments": ["acknowledgments", "acknowledgements"],
    }

    def __init__(
        self,
        *,
        max_chunk_size: int = 2000,  # Max characters per chunk
        min_chunk_size: int = 100,  # Min characters per chunk
        preserve_equations: bool = True,
        preserve_citations: bool = True,
    ):
        """Initialize semantic chunker.

        Args:
            max_chunk_size: Maximum chunk size in characters
            min_chunk_size: Minimum chunk size in characters
            preserve_equations: Keep equations with surrounding context
            preserve_citations: Keep citations with surrounding context
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.preserve_equations = preserve_equations
        self.preserve_citations = preserve_citations

    def _classify_section_type(self, section_title: str) -> str:
        """Classify section into standard types.

        Args:
            section_title: Section title

        Returns:
            Section type (e.g., "introduction", "methods", etc.)
        """
        title_lower = section_title.lower().strip()

        for section_type, keywords in self.SECTION_TYPES.items():
            if any(keyword in title_lower for keyword in keywords):
                return section_type

        # Default to generic "section"
        return "section"

    def _extract_equations_from_content(self, content: str) -> list[str]:
        """Extract equation references from content.

        Args:
            content: Text content

        Returns:
            List of equation strings
        """
        import re

        equations = []

        # Display equations
        display_pattern = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
        equations.extend(m.group(1).strip() for m in display_pattern.finditer(content))

        # Inline equations (only longer ones to avoid noise)
        inline_pattern = re.compile(r"\$([^$]{4,})\$")
        equations.extend(m.group(1).strip() for m in inline_pattern.finditer(content))

        return equations

    def _extract_citation_ids_from_content(self, content: str) -> list[str]:
        """Extract citation IDs from content.

        Args:
            content: Text content

        Returns:
            List of citation IDs (arXiv IDs or DOIs)
        """
        import re

        citation_ids = []

        # arXiv IDs
        arxiv_pattern = re.compile(r"(?:arXiv:)?(\d{4}\.\d{4,5}(?:v\d+)?)")
        citation_ids.extend(m.group(1) for m in arxiv_pattern.finditer(content))

        # DOIs
        doi_pattern = re.compile(r"10\.\d{4,}/[^\s]+")
        citation_ids.extend(m.group(0) for m in doi_pattern.finditer(content))

        return list(set(citation_ids))  # Deduplicate

    def _split_large_section(self, section: Section, arxiv_id: str, position: int) -> list[PaperChunk]:
        """Split large section into smaller chunks.

        Args:
            section: Section to split
            arxiv_id: Paper arXiv ID
            position: Starting position

        Returns:
            List of chunks
        """
        chunks: list[PaperChunk] = []

        # Split by paragraphs
        paragraphs = section.content.split("\n\n")

        current_content = []
        current_length = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_length = len(para)

            # If adding this paragraph exceeds max size, create a chunk
            if current_content and current_length + para_length > self.max_chunk_size:
                content = "\n\n".join(current_content)
                section_type = self._classify_section_type(section.title)

                chunks.append(
                    PaperChunk(
                        arxiv_id=arxiv_id,
                        section_type=section_type,
                        title=section.title,
                        content=content,
                        equations=self._extract_equations_from_content(content),
                        citations=self._extract_citation_ids_from_content(content),
                        position=position + len(chunks),
                        level=section.level,
                        word_count=len(content.split()),
                        char_count=len(content),
                    )
                )

                current_content = [para]
                current_length = para_length
            else:
                current_content.append(para)
                current_length += para_length + 2  # +2 for \n\n

        # Don't forget remaining content
        if current_content:
            content = "\n\n".join(current_content)
            section_type = self._classify_section_type(section.title)

            chunks.append(
                PaperChunk(
                    arxiv_id=arxiv_id,
                    section_type=section_type,
                    title=section.title,
                    content=content,
                    equations=self._extract_equations_from_content(content),
                    citations=self._extract_citation_ids_from_content(content),
                    position=position + len(chunks),
                    level=section.level,
                    word_count=len(content.split()),
                    char_count=len(content),
                )
            )

        return chunks

    def chunk_paper(self, paper: ParsedPaper) -> list[PaperChunk]:
        """Chunk a parsed paper into semantic units.

        Args:
            paper: Parsed paper

        Returns:
            List of chunks
        """
        chunks: list[PaperChunk] = []
        position = 0

        # Always create abstract chunk first
        if paper.abstract:
            chunks.append(
                PaperChunk(
                    arxiv_id=paper.arxiv_id,
                    section_type="abstract",
                    title="Abstract",
                    content=paper.abstract,
                    equations=self._extract_equations_from_content(paper.abstract),
                    citations=self._extract_citation_ids_from_content(paper.abstract),
                    position=position,
                    level=1,
                    word_count=len(paper.abstract.split()),
                    char_count=len(paper.abstract),
                    metadata={"is_abstract": True},
                )
            )
            position += 1

        # Process sections
        for section in paper.sections:
            # Skip empty sections
            if not section.content or len(section.content) < self.min_chunk_size:
                continue

            section_type = self._classify_section_type(section.title)

            # If section is small enough, create single chunk
            if len(section.content) <= self.max_chunk_size:
                chunks.append(
                    PaperChunk(
                        arxiv_id=paper.arxiv_id,
                        section_type=section_type,
                        title=section.title,
                        content=section.content,
                        equations=section.equations or self._extract_equations_from_content(section.content),
                        citations=self._extract_citation_ids_from_content(section.content),
                        position=position,
                        level=section.level,
                        word_count=len(section.content.split()),
                        char_count=len(section.content),
                    )
                )
                position += 1
            else:
                # Split large section
                section_chunks = self._split_large_section(section, paper.arxiv_id, position)
                chunks.extend(section_chunks)
                position += len(section_chunks)

        logger.info(
            "chunked_paper",
            arxiv_id=paper.arxiv_id,
            total_chunks=len(chunks),
            avg_chunk_size=sum(c.char_count for c in chunks) // len(chunks) if chunks else 0,
        )

        return chunks

    def get_chunk_statistics(self, chunks: list[PaperChunk]) -> dict[str, Any]:
        """Get statistics about chunks.

        Args:
            chunks: List of chunks

        Returns:
            Dictionary of statistics
        """
        if not chunks:
            return {}

        section_types = [c.section_type for c in chunks]
        char_counts = [c.char_count for c in chunks]
        word_counts = [c.word_count for c in chunks]

        return {
            "total_chunks": len(chunks),
            "section_types": dict((t, section_types.count(t)) for t in set(section_types)),
            "avg_char_count": sum(char_counts) / len(char_counts),
            "avg_word_count": sum(word_counts) / len(word_counts),
            "min_char_count": min(char_counts),
            "max_char_count": max(char_counts),
            "total_equations": sum(len(c.equations) for c in chunks),
            "total_citations": sum(len(c.citations) for c in chunks),
        }


def chunk_parsed_paper(
    paper: ParsedPaper,
    max_chunk_size: int = 2000,
    min_chunk_size: int = 100,
) -> list[PaperChunk]:
    """Convenience function to chunk a parsed paper.

    Args:
        paper: Parsed paper
        max_chunk_size: Maximum chunk size in characters
        min_chunk_size: Minimum chunk size in characters

    Returns:
        List of chunks
    """
    chunker = SemanticChunker(
        max_chunk_size=max_chunk_size,
        min_chunk_size=min_chunk_size,
    )
    return chunker.chunk_paper(paper)