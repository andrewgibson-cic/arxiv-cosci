"""Batch processing utilities for large-scale paper ingestion.

Provides async batch processing with progress tracking, error handling,
and resource management for processing thousands of papers efficiently.
"""

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import structlog
from tqdm.asyncio import tqdm

from packages.ingestion.models import ParsedPaper
from packages.ingestion.s2_client import S2Client
from packages.ingestion.text_extractor import parse_pdf_file
from packages.knowledge.chromadb_client import chromadb_client
from packages.knowledge.neo4j_client import neo4j_client

logger = structlog.get_logger()

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    batch_size: int = 100
    """Number of items to process in each batch."""

    max_concurrent: int = 10
    """Maximum concurrent operations."""

    retry_attempts: int = 3
    """Number of retry attempts for failed items."""

    checkpoint_interval: int = 500
    """Save checkpoint every N items."""

    checkpoint_dir: Path | None = None
    """Directory to save checkpoints."""


@dataclass
class BatchResult:
    """Result of batch processing operation."""

    total: int
    """Total items processed."""

    successful: int
    """Successfully processed items."""

    failed: int
    """Failed items."""

    errors: list[tuple[Any, Exception]]
    """List of (item, error) tuples."""

    checkpoints: list[Path]
    """Checkpoint files created."""


class BatchProcessor:
    """Async batch processor with progress tracking."""

    def __init__(self, config: BatchConfig | None = None) -> None:
        """Initialize batch processor.

        Args:
            config: Batch processing configuration
        """
        self.config = config or BatchConfig()
        self._checkpoint_counter = 0

    async def process_items(
        self,
        items: list[T],
        process_fn: Callable[[T], Coroutine[Any, Any, R]],
        *,
        desc: str = "Processing",
    ) -> BatchResult:
        """Process items in batches with progress tracking.

        Args:
            items: List of items to process
            process_fn: Async function to process each item
            desc: Progress bar description

        Returns:
            BatchResult with statistics
        """
        total = len(items)
        successful = 0
        failed = 0
        errors: list[tuple[Any, Exception]] = []
        checkpoints: list[Path] = []

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def process_with_semaphore(item: T) -> tuple[bool, T | None, Exception | None]:
            """Process single item with concurrency limit."""
            async with semaphore:
                for attempt in range(self.config.retry_attempts):
                    try:
                        await process_fn(item)
                        return (True, item, None)
                    except Exception as e:
                        if attempt == self.config.retry_attempts - 1:
                            logger.error(
                                "item_failed",
                                item=str(item)[:100],
                                error=str(e),
                                attempts=attempt + 1,
                            )
                            return (False, item, e)
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                return (False, item, None)

        # Process in batches with progress bar
        with tqdm(total=total, desc=desc) as pbar:
            for i in range(0, total, self.config.batch_size):
                batch = items[i : i + self.config.batch_size]

                # Process batch concurrently
                results = await asyncio.gather(
                    *[process_with_semaphore(item) for item in batch],
                    return_exceptions=False,
                )

                # Collect results
                for success, item, error in results:
                    if success:
                        successful += 1
                    else:
                        failed += 1
                        if error:
                            errors.append((item, error))

                    pbar.update(1)

                # Checkpoint if needed
                if self.config.checkpoint_dir and (i + len(batch)) % self.config.checkpoint_interval == 0:
                    checkpoint = await self._save_checkpoint(
                        processed=i + len(batch),
                        total=total,
                        successful=successful,
                        failed=failed,
                    )
                    if checkpoint:
                        checkpoints.append(checkpoint)

        return BatchResult(
            total=total,
            successful=successful,
            failed=failed,
            errors=errors,
            checkpoints=checkpoints,
        )

    async def _save_checkpoint(
        self,
        processed: int,
        total: int,
        successful: int,
        failed: int,
    ) -> Path | None:
        """Save processing checkpoint."""
        if not self.config.checkpoint_dir:
            return None

        self.config.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._checkpoint_counter += 1

        checkpoint_file = self.config.checkpoint_dir / f"checkpoint_{self._checkpoint_counter}.json"

        import json

        data = {
            "processed": processed,
            "total": total,
            "successful": successful,
            "failed": failed,
            "progress": f"{processed / total * 100:.1f}%",
        }

        checkpoint_file.write_text(json.dumps(data, indent=2))
        logger.info("checkpoint_saved", file=str(checkpoint_file), **data)

        return checkpoint_file


class PaperBatchIngester:
    """Specialized batch processor for paper ingestion."""

    def __init__(self, config: BatchConfig | None = None) -> None:
        """Initialize paper batch ingester.

        Args:
            config: Batch processing configuration
        """
        self.config = config or BatchConfig(
            batch_size=50,
            max_concurrent=5,
            checkpoint_interval=250,
        )
        self.processor = BatchProcessor(self.config)

    async def ingest_papers_to_neo4j(
        self,
        papers: list[ParsedPaper],
    ) -> BatchResult:
        """Ingest papers to Neo4j in batches.

        Args:
            papers: List of parsed papers

        Returns:
            BatchResult with statistics
        """
        await neo4j_client.connect()

        try:
            async def ingest_paper(paper: ParsedPaper) -> None:
                """Ingest single paper to Neo4j."""
                await neo4j_client.ingest_paper(paper, include_citations=True)

            result = await self.processor.process_items(
                papers,
                ingest_paper,
                desc="Ingesting to Neo4j",
            )

            logger.info(
                "neo4j_batch_complete",
                total=result.total,
                successful=result.successful,
                failed=result.failed,
            )

            return result

        finally:
            await neo4j_client.close()

    async def ingest_papers_to_chromadb(
        self,
        papers: list[ParsedPaper],
    ) -> BatchResult:
        """Ingest papers to ChromaDB in batches.

        Args:
            papers: List of parsed papers

        Returns:
            BatchResult with statistics
        """
        async def ingest_paper(paper: ParsedPaper) -> None:
            """Ingest single paper to ChromaDB."""
            chromadb_client.add_paper(paper)

        result = await self.processor.process_items(
            papers,
            ingest_paper,
            desc="Ingesting to ChromaDB",
        )

        logger.info(
            "chromadb_batch_complete",
            total=result.total,
            successful=result.successful,
            failed=result.failed,
        )

        return result

    async def ingest_papers_full(
        self,
        papers: list[ParsedPaper],
        *,
        to_neo4j: bool = True,
        to_chromadb: bool = True,
    ) -> dict[str, BatchResult]:
        """Ingest papers to both databases in batches.

        Args:
            papers: List of parsed papers
            to_neo4j: Whether to ingest to Neo4j
            to_chromadb: Whether to ingest to ChromaDB

        Returns:
            Dictionary with results for each database
        """
        results: dict[str, BatchResult] = {}

        if to_neo4j:
            logger.info("starting_neo4j_ingestion", count=len(papers))
            results["neo4j"] = await self.ingest_papers_to_neo4j(papers)

        if to_chromadb:
            logger.info("starting_chromadb_ingestion", count=len(papers))
            results["chromadb"] = await self.ingest_papers_to_chromadb(papers)

        return results


class PDFBatchParser:
    """Specialized batch processor for PDF parsing."""

    def __init__(self, config: BatchConfig | None = None) -> None:
        """Initialize PDF batch parser.

        Args:
            config: Batch processing configuration
        """
        self.config = config or BatchConfig(
            batch_size=20,
            max_concurrent=3,
            checkpoint_interval=100,
        )
        self.processor = BatchProcessor(self.config)

    async def parse_pdfs(
        self,
        pdf_files: list[Path],
        output_dir: Path,
    ) -> BatchResult:
        """Parse PDF files in batches.

        Args:
            pdf_files: List of PDF file paths
            output_dir: Directory to save parsed output

        Returns:
            BatchResult with statistics
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        async def parse_pdf(pdf_path: Path) -> None:
            """Parse single PDF file."""
            # Run sync parsing in thread pool
            loop = asyncio.get_event_loop()
            parsed = await loop.run_in_executor(None, parse_pdf_file, pdf_path)

            # Save output
            output_file = output_dir / f"{parsed.arxiv_id.replace('/', '_')}.json"
            output_file.write_text(parsed.model_dump_json(indent=2))

        result = await self.processor.process_items(
            pdf_files,
            parse_pdf,
            desc="Parsing PDFs",
        )

        logger.info(
            "pdf_batch_complete",
            total=result.total,
            successful=result.successful,
            failed=result.failed,
        )

        return result


async def batch_fetch_from_s2(
    arxiv_ids: list[str],
    output_file: Path | None = None,
) -> BatchResult:
    """Fetch papers from Semantic Scholar in batches.

    Args:
        arxiv_ids: List of arXiv IDs to fetch
        output_file: Optional file to save results

    Returns:
        BatchResult with statistics
    """
    config = BatchConfig(batch_size=10, max_concurrent=5)
    processor = BatchProcessor(config)

    client = S2Client()
    papers: list[dict[str, Any]] = []

    async def fetch_paper(arxiv_id: str) -> None:
        """Fetch single paper from S2."""
        paper = await client.get_paper_by_arxiv_id(arxiv_id)
        if paper:
            metadata = client.paper_to_metadata(paper)
            papers.append(metadata.model_dump())

    result = await processor.process_items(
        arxiv_ids,
        fetch_paper,
        desc="Fetching from S2",
    )

    # Save results if requested
    if output_file and papers:
        import json

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(papers, indent=2))
        logger.info("papers_saved", file=str(output_file), count=len(papers))

    return result
