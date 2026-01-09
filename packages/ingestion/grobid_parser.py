"""Grobid-based citation and metadata extraction.

Grobid is specialized for extracting structured metadata from scientific PDFs:
- Paper metadata (title, authors, affiliations)
- Citations with context
- Reference lists with full bibliographic info
- Section structure
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
import structlog
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from packages.ingestion.models import ArxivPaper, Citation, CitationIntent, ParsedPaper

logger = structlog.get_logger()

# Grobid service configuration
DEFAULT_GROBID_URL = "http://localhost:8070"
GROBID_TIMEOUT = 300  # 5 minutes for large papers


class GrobidConfig:
    """Configuration for Grobid parser."""

    def __init__(
        self,
        *,
        service_url: str = DEFAULT_GROBID_URL,
        timeout: int = GROBID_TIMEOUT,
        consolidate_citations: bool = True,
        consolidate_header: bool = True,
    ):
        """Initialize Grobid configuration.

        Args:
            service_url: Grobid service URL
            timeout: Request timeout in seconds
            consolidate_citations: Consolidate citations with external services
            consolidate_header: Consolidate header metadata
        """
        self.service_url = service_url.rstrip("/")
        self.timeout = timeout
        self.consolidate_citations = consolidate_citations
        self.consolidate_header = consolidate_header


class GrobidParser:
    """PDF parser using Grobid for citation and metadata extraction."""

    def __init__(self, config: GrobidConfig | None = None):
        """Initialize Grobid parser.

        Args:
            config: Parser configuration
        """
        self.config = config or GrobidConfig()
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def check_service_health(self) -> bool:
        """Check if Grobid service is available.

        Returns:
            True if service is healthy
        """
        try:
            session = await self._get_session()
            url = f"{self.config.service_url}/api/isalive"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status == 200
        except Exception as e:
            logger.warning("grobid_health_check_failed", error=str(e))
            return False

    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    async def process_pdf(self, pdf_path: Path) -> str:
        """Process PDF with Grobid and return TEI XML.

        Args:
            pdf_path: Path to PDF file

        Returns:
            TEI XML string

        Raises:
            FileNotFoundError: If PDF doesn't exist
            RuntimeError: If Grobid processing fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info("processing_with_grobid", pdf_path=str(pdf_path))

        session = await self._get_session()
        url = f"{self.config.service_url}/api/processFulltextDocument"

        # Prepare form data
        data = aiohttp.FormData()
        data.add_field(
            "input",
            open(pdf_path, "rb"),
            filename=pdf_path.name,
            content_type="application/pdf",
        )
        data.add_field("consolidateCitations", str(int(self.config.consolidate_citations)))
        data.add_field("consolidateHeader", str(int(self.config.consolidate_header)))

        try:
            async with session.post(url, data=data) as response:
                if response.status == 503:
                    raise RuntimeError("Grobid service unavailable")

                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(
                        f"Grobid returned status {response.status}: {error_text}"
                    )

                tei_xml = await response.text()
                logger.info("grobid_parse_complete", xml_length=len(tei_xml))
                return tei_xml

        except Exception as e:
            logger.error("grobid_processing_failed", error=str(e), pdf_path=str(pdf_path))
            raise

    def _extract_metadata_from_tei(self, tei_xml: str) -> dict[str, Any]:
        """Extract metadata from TEI XML.

        Args:
            tei_xml: TEI XML string

        Returns:
            Dictionary of metadata
        """
        soup = BeautifulSoup(tei_xml, "xml")

        metadata: dict[str, Any] = {}

        # Extract title
        title_tag = soup.find("title", {"level": "a", "type": "main"})
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)

        # Extract authors
        authors = []
        for author in soup.find_all("author"):
            persname = author.find("persName")
            if persname:
                forename = persname.find("forename", {"type": "first"})
                surname = persname.find("surname")
                if forename and surname:
                    name = f"{forename.get_text(strip=True)} {surname.get_text(strip=True)}"
                    authors.append(name)
        metadata["authors"] = authors

        # Extract abstract
        abstract_div = soup.find("div", {"type": "abstract"})
        if abstract_div:
            abstract_p = abstract_div.find("p")
            if abstract_p:
                metadata["abstract"] = abstract_p.get_text(strip=True)

        return metadata

    def _extract_citations_from_tei(self, tei_xml: str) -> list[Citation]:
        """Extract citations with context from TEI XML.

        Args:
            tei_xml: TEI XML string

        Returns:
            List of citations
        """
        soup = BeautifulSoup(tei_xml, "xml")
        citations: list[Citation] = []

        # Find all reference pointers in text
        for ref in soup.find_all("ref", {"type": "bibr"}):
            target = ref.get("target", "")
            if not target:
                continue

            # Get surrounding context
            parent = ref.parent
            if parent:
                context = parent.get_text(strip=True)
            else:
                context = ref.get_text(strip=True)

            # Find the referenced bibliography entry
            ref_id = target.lstrip("#")
            bib_entry = soup.find("biblStruct", {"xml:id": ref_id})

            if bib_entry:
                # Extract identifiers
                arxiv_id = None
                doi = None

                # Check for arXiv ID
                for idno in bib_entry.find_all("idno"):
                    idno_type = idno.get("type", "").lower()
                    if idno_type == "arxiv":
                        arxiv_id = idno.get_text(strip=True)
                    elif idno_type == "doi":
                        doi = idno.get_text(strip=True)

                # Get raw reference text
                raw_text = bib_entry.get_text(separator=" ", strip=True)

                citation = Citation(
                    raw_text=raw_text[:200],  # Limit length
                    arxiv_id=arxiv_id,
                    doi=doi,
                    context=context[:500],  # Limit context length
                    intent=CitationIntent.UNKNOWN,  # Will be classified later
                )
                citations.append(citation)

        logger.debug("extracted_citations", count=len(citations))
        return citations

    def _extract_sections_from_tei(self, tei_xml: str) -> list[dict[str, Any]]:
        """Extract section structure from TEI XML.

        Args:
            tei_xml: TEI XML string

        Returns:
            List of section dictionaries
        """
        soup = BeautifulSoup(tei_xml, "xml")
        sections = []

        # Find all div elements (sections)
        for div in soup.find_all("div"):
            head = div.find("head")
            if head:
                title = head.get_text(strip=True)

                # Get section content
                paragraphs = div.find_all("p")
                content = "\n\n".join(p.get_text(strip=True) for p in paragraphs)

                # Determine level from nesting
                level = len(list(div.parents)) - len(list(soup.parents))
                level = max(1, min(level, 6))

                sections.append({"title": title, "content": content, "level": level})

        logger.debug("extracted_sections", count=len(sections))
        return sections

    async def parse(
        self, paper: ArxivPaper, output_dir: Path | None = None
    ) -> tuple[str, dict[str, Any]]:
        """Parse paper with Grobid.

        Args:
            paper: ArxivPaper with pdf_path
            output_dir: Optional directory to save TEI XML

        Returns:
            Tuple of (tei_xml, parsed_data_dict)

        Raises:
            ValueError: If PDF path not available
            RuntimeError: If parsing fails
        """
        if not paper.pdf_path or not paper.pdf_path.exists():
            raise ValueError(f"No PDF available for {paper.arxiv_id}")

        # Check service health
        if not await self.check_service_health():
            raise RuntimeError(
                f"Grobid service not available at {self.config.service_url}. "
                "Start with: docker compose up -d grobid"
            )

        logger.info("parsing_paper_with_grobid", arxiv_id=paper.arxiv_id)

        # Process PDF
        tei_xml = await self.process_pdf(paper.pdf_path)

        # Save TEI XML if output directory provided
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            xml_path = output_dir / f"{paper.arxiv_id.replace('/', '_')}_grobid.xml"
            xml_path.write_text(tei_xml, encoding="utf-8")
            logger.debug("saved_tei_xml", path=str(xml_path))

        # Extract structured data
        metadata = self._extract_metadata_from_tei(tei_xml)
        citations = self._extract_citations_from_tei(tei_xml)
        sections = self._extract_sections_from_tei(tei_xml)

        parsed_data = {
            "metadata": metadata,
            "citations": citations,
            "sections": sections,
            "tei_xml": tei_xml,
        }

        return tei_xml, parsed_data


async def parse_with_grobid(
    paper: ArxivPaper,
    output_dir: Path | None = None,
    config: GrobidConfig | None = None,
) -> tuple[str, dict[str, Any]]:
    """Convenience function to parse paper with Grobid.

    Args:
        paper: ArxivPaper with pdf_path
        output_dir: Optional directory to save TEI XML
        config: Optional parser configuration

    Returns:
        Tuple of (tei_xml, parsed_data_dict)
    """
    parser = GrobidParser(config)
    try:
        return await parser.parse(paper, output_dir)
    finally:
        await parser.close()