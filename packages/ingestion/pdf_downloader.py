"""Rate-limited PDF downloader for arXiv papers.

Respects arXiv's rate limits and politeness policies:
- Maximum 1 request per 3 seconds
- Exponential backoff on errors
- Proper User-Agent identification
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from packages.ingestion.models import ArxivPaper, PaperMetadata

logger = structlog.get_logger()

# arXiv rate limit: 1 request per 3 seconds
ARXIV_RATE_LIMIT_SECONDS = 3.0

# User-Agent as recommended by arXiv
USER_AGENT = "arxiv-cosci/0.1.0 (https://github.com/yourusername/arxiv-cosci; mailto:your@email.com)"

# Connection settings
TIMEOUT_SECONDS = 60
MAX_RETRIES = 3


class RateLimiter:
    """Token bucket rate limiter for API requests."""

    def __init__(self, min_interval: float = ARXIV_RATE_LIMIT_SECONDS):
        self.min_interval = min_interval
        self._last_request: float = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request is allowed."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self._last_request = asyncio.get_event_loop().time()


class ArxivDownloader:
    """Async PDF downloader with rate limiting."""

    def __init__(
        self,
        output_dir: Path,
        *,
        rate_limit: float = ARXIV_RATE_LIMIT_SECONDS,
    ):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limiter = RateLimiter(rate_limit)
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": USER_AGENT},
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_pdf_path(self, arxiv_id: str) -> Path:
        """Get the local path for a PDF.

        Organizes by year-month prefix for better filesystem performance.
        """
        # Extract year-month from ID (e.g., "2401.12345" -> "2401")
        prefix = arxiv_id.split(".")[0] if "." in arxiv_id else arxiv_id[:4]
        subdir = self.output_dir / prefix
        subdir.mkdir(exist_ok=True)
        return subdir / f"{arxiv_id.replace('/', '_')}.pdf"

    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=4, max=60),
    )
    async def _download_pdf(self, arxiv_id: str) -> Path:
        """Download a single PDF with retry logic."""
        pdf_path = self._get_pdf_path(arxiv_id)

        # Skip if already downloaded
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            logger.debug("pdf_exists", arxiv_id=arxiv_id, path=str(pdf_path))
            return pdf_path

        await self.rate_limiter.acquire()

        url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        session = await self._get_session()

        logger.debug("downloading_pdf", arxiv_id=arxiv_id, url=url)

        async with session.get(url) as response:
            if response.status == 404:
                raise FileNotFoundError(f"PDF not found: {arxiv_id}")

            if response.status == 429:
                # Rate limited - wait and retry
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning("rate_limited", arxiv_id=arxiv_id, retry_after=retry_after)
                await asyncio.sleep(retry_after)
                raise aiohttp.ClientError("Rate limited")

            response.raise_for_status()

            content = await response.read()

            # Validate PDF
            if not content.startswith(b"%PDF"):
                raise ValueError(f"Invalid PDF content for {arxiv_id}")

            pdf_path.write_bytes(content)
            logger.info("pdf_downloaded", arxiv_id=arxiv_id, size=len(content))

        return pdf_path

    async def download(self, metadata: PaperMetadata) -> ArxivPaper:
        """Download PDF for a paper.

        Args:
            metadata: Paper metadata

        Returns:
            ArxivPaper with pdf_path set

        Raises:
            Various exceptions on download failure
        """
        pdf_path = await self._download_pdf(metadata.id)
        return ArxivPaper(
            metadata=metadata,
            pdf_path=pdf_path,
            downloaded_at=datetime.now(),
        )

    async def download_batch(
        self,
        papers: list[PaperMetadata],
        *,
        skip_errors: bool = True,
    ) -> list[ArxivPaper]:
        """Download PDFs for multiple papers sequentially.

        Note: Sequential due to arXiv rate limits. For parallel downloading
        from multiple sources, use separate sessions.

        Args:
            papers: List of paper metadata
            skip_errors: If True, continue on individual failures

        Returns:
            List of successfully downloaded papers
        """
        results: list[ArxivPaper] = []

        for i, metadata in enumerate(papers):
            try:
                paper = await self.download(metadata)
                results.append(paper)

                if (i + 1) % 10 == 0:
                    logger.info("download_progress", completed=i + 1, total=len(papers))

            except Exception as e:
                logger.error("download_failed", arxiv_id=metadata.id, error=str(e))
                if not skip_errors:
                    raise

        return results


async def download_papers(
    papers: list[PaperMetadata],
    output_dir: Path,
    *,
    skip_errors: bool = True,
) -> list[ArxivPaper]:
    """Convenience function to download multiple papers.

    Args:
        papers: List of paper metadata
        output_dir: Directory for downloaded PDFs
        skip_errors: If True, continue on individual failures

    Returns:
        List of successfully downloaded papers
    """
    downloader = ArxivDownloader(output_dir)
    try:
        return await downloader.download_batch(papers, skip_errors=skip_errors)
    finally:
        await downloader.close()
