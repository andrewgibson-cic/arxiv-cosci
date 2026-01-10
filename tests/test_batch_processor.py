"""Tests for batch processing utilities."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.ingestion.batch_processor import (
    BatchConfig,
    BatchProcessor,
    BatchResult,
    PaperBatchIngester,
    PDFBatchParser,
    batch_fetch_from_s2,
)
from packages.ingestion.models import ParsedPaper


@pytest.fixture
def batch_config():
    """Create test batch configuration."""
    return BatchConfig(
        batch_size=10,
        max_concurrent=3,
        retry_attempts=2,
        checkpoint_interval=20,
        checkpoint_dir=Path("data/test_checkpoints"),
    )


@pytest.fixture
def sample_papers():
    """Create sample papers for testing."""
    papers = []
    for i in range(25):
        paper = ParsedPaper(
            arxiv_id=f"2024.{i:05d}",
            title=f"Test Paper {i}",
            abstract=f"Abstract for paper {i}",
            authors=["Author A", "Author B"],
            categories=["cs.AI"],
            full_text=f"Full text of paper {i}",
            sections=[],
            citations=[],
            published_date="2024-01-01",
        )
        papers.append(paper)
    return papers


class TestBatchConfig:
    """Test BatchConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BatchConfig()
        assert config.batch_size == 100
        assert config.max_concurrent == 10
        assert config.retry_attempts == 3
        assert config.checkpoint_interval == 500
        assert config.checkpoint_dir is None

    def test_custom_config(self, batch_config):
        """Test custom configuration."""
        assert batch_config.batch_size == 10
        assert batch_config.max_concurrent == 3
        assert batch_config.retry_attempts == 2
        assert batch_config.checkpoint_interval == 20


class TestBatchProcessor:
    """Test BatchProcessor class."""

    @pytest.mark.asyncio
    async def test_process_items_success(self, batch_config):
        """Test successful processing of all items."""
        processor = BatchProcessor(batch_config)
        items = list(range(25))
        processed = []

        async def process_fn(item: int) -> None:
            processed.append(item)
            await asyncio.sleep(0.01)

        result = await processor.process_items(items, process_fn, desc="Testing")

        assert result.total == 25
        assert result.successful == 25
        assert result.failed == 0
        assert len(result.errors) == 0
        assert len(processed) == 25

    @pytest.mark.asyncio
    async def test_process_items_with_failures(self, batch_config):
        """Test processing with some failures."""
        processor = BatchProcessor(batch_config)
        items = list(range(10))

        async def process_fn(item: int) -> None:
            if item % 3 == 0:
                raise ValueError(f"Error processing {item}")
            await asyncio.sleep(0.01)

        result = await processor.process_items(items, process_fn)

        assert result.total == 10
        assert result.successful == 6  # 1,2,4,5,7,8
        assert result.failed == 4  # 0,3,6,9
        assert len(result.errors) == 4

    @pytest.mark.asyncio
    async def test_process_items_retry_logic(self, batch_config):
        """Test retry logic for failed items."""
        processor = BatchProcessor(batch_config)
        items = [1, 2, 3]
        attempt_counts = {1: 0, 2: 0, 3: 0}

        async def process_fn(item: int) -> None:
            attempt_counts[item] += 1
            if attempt_counts[item] < 2:
                raise ValueError("Temporary failure")
            await asyncio.sleep(0.01)

        result = await processor.process_items(items, process_fn)

        assert result.total == 3
        assert result.successful == 3
        assert all(count == 2 for count in attempt_counts.values())

    @pytest.mark.asyncio
    async def test_checkpoint_creation(self, batch_config, tmp_path):
        """Test checkpoint file creation."""
        batch_config.checkpoint_dir = tmp_path
        processor = BatchProcessor(batch_config)
        items = list(range(50))

        async def process_fn(item: int) -> None:
            await asyncio.sleep(0.001)

        result = await processor.process_items(items, process_fn)

        assert result.total == 50
        assert len(result.checkpoints) > 0
        assert all(cp.exists() for cp in result.checkpoints)

    @pytest.mark.asyncio
    async def test_concurrency_limit(self, batch_config):
        """Test that concurrency is limited."""
        processor = BatchProcessor(batch_config)
        items = list(range(20))
        active_count = 0
        max_active = 0

        async def process_fn(item: int) -> None:
            nonlocal active_count, max_active
            active_count += 1
            max_active = max(max_active, active_count)
            await asyncio.sleep(0.05)
            active_count -= 1

        await processor.process_items(items, process_fn)

        assert max_active <= batch_config.max_concurrent


class TestPaperBatchIngester:
    """Test PaperBatchIngester class."""

    @pytest.mark.asyncio
    async def test_ingest_papers_to_neo4j(self, sample_papers, batch_config):
        """Test batch ingestion to Neo4j."""
        ingester = PaperBatchIngester(batch_config)

        with patch("packages.ingestion.batch_processor.neo4j_client") as mock_client:
            mock_client.connect = AsyncMock()
            mock_client.close = AsyncMock()
            mock_client.ingest_paper = AsyncMock()

            result = await ingester.ingest_papers_to_neo4j(sample_papers[:10])

            assert result.total == 10
            assert result.successful == 10
            assert mock_client.connect.called
            assert mock_client.close.called
            assert mock_client.ingest_paper.call_count == 10

    @pytest.mark.asyncio
    async def test_ingest_papers_to_chromadb(self, sample_papers, batch_config):
        """Test batch ingestion to ChromaDB."""
        ingester = PaperBatchIngester(batch_config)

        with patch("packages.ingestion.batch_processor.chromadb_client") as mock_client:
            mock_client.add_paper = MagicMock()

            result = await ingester.ingest_papers_to_chromadb(sample_papers[:10])

            assert result.total == 10
            assert result.successful == 10
            assert mock_client.add_paper.call_count == 10

    @pytest.mark.asyncio
    async def test_ingest_papers_full(self, sample_papers, batch_config):
        """Test full ingestion to both databases."""
        ingester = PaperBatchIngester(batch_config)

        with patch("packages.ingestion.batch_processor.neo4j_client") as mock_neo4j, \
             patch("packages.ingestion.batch_processor.chromadb_client") as mock_chroma:
            
            mock_neo4j.connect = AsyncMock()
            mock_neo4j.close = AsyncMock()
            mock_neo4j.ingest_paper = AsyncMock()
            mock_chroma.add_paper = MagicMock()

            results = await ingester.ingest_papers_full(
                sample_papers[:5],
                to_neo4j=True,
                to_chromadb=True,
            )

            assert "neo4j" in results
            assert "chromadb" in results
            assert results["neo4j"].total == 5
            assert results["chromadb"].total == 5


class TestPDFBatchParser:
    """Test PDFBatchParser class."""

    @pytest.mark.asyncio
    async def test_parse_pdfs(self, batch_config, tmp_path):
        """Test batch PDF parsing."""
        parser = PDFBatchParser(batch_config)
        
        # Create dummy PDF files
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        pdf_files = []
        for i in range(5):
            pdf_file = pdf_dir / f"paper_{i}.pdf"
            pdf_file.write_text(f"PDF content {i}")
            pdf_files.append(pdf_file)

        output_dir = tmp_path / "output"

        # Mock the PDF parser
        with patch("packages.ingestion.batch_processor.parse_pdf_file") as mock_parse:
            def create_parsed_paper(pdf_path):
                return ParsedPaper(
                    arxiv_id=f"2024.{pdf_path.stem}",
                    title=f"Paper from {pdf_path.name}",
                    abstract="Test abstract",
                    authors=["Test Author"],
                    categories=["cs.AI"],
                    full_text="Test content",
                    sections=[],
                    citations=[],
                    published_date="2024-01-01",
                )
            
            mock_parse.side_effect = create_parsed_paper

            result = await parser.parse_pdfs(pdf_files, output_dir)

            assert result.total == 5
            assert result.successful == 5
            assert mock_parse.call_count == 5
            assert output_dir.exists()


class TestBatchFetchFromS2:
    """Test batch fetching from Semantic Scholar."""

    @pytest.mark.asyncio
    async def test_batch_fetch_success(self, tmp_path):
        """Test successful batch fetching."""
        arxiv_ids = [f"2024.{i:05d}" for i in range(5)]
        output_file = tmp_path / "papers.json"

        with patch("packages.ingestion.batch_processor.S2Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            async def mock_get_paper(arxiv_id):
                return {"paperId": f"s2_{arxiv_id}", "title": f"Paper {arxiv_id}"}

            mock_client.get_paper_by_arxiv_id = AsyncMock(side_effect=mock_get_paper)
            mock_client.paper_to_metadata = MagicMock(
                return_value=MagicMock(model_dump=lambda: {"arxiv_id": "test"})
            )

            result = await batch_fetch_from_s2(arxiv_ids, output_file)

            assert result.total == 5
            assert result.successful == 5
            assert output_file.exists()

    @pytest.mark.asyncio
    async def test_batch_fetch_with_failures(self):
        """Test batch fetching with some failures."""
        arxiv_ids = [f"2024.{i:05d}" for i in range(5)]

        with patch("packages.ingestion.batch_processor.S2Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            async def mock_get_paper(arxiv_id):
                if "00002" in arxiv_id:
                    return None  # Paper not found
                return {"paperId": f"s2_{arxiv_id}"}

            mock_client.get_paper_by_arxiv_id = AsyncMock(side_effect=mock_get_paper)
            mock_client.paper_to_metadata = MagicMock(
                return_value=MagicMock(model_dump=lambda: {"arxiv_id": "test"})
            )

            result = await batch_fetch_from_s2(arxiv_ids)

            assert result.total == 5
            # Should succeed for all (None papers are just skipped)
            assert result.successful == 5


class TestBatchResult:
    """Test BatchResult dataclass."""

    def test_batch_result_creation(self):
        """Test creating a BatchResult."""
        result = BatchResult(
            total=100,
            successful=95,
            failed=5,
            errors=[(1, ValueError("Error 1")), (2, ValueError("Error 2"))],
            checkpoints=[Path("checkpoint1.json")],
        )

        assert result.total == 100
        assert result.successful == 95
        assert result.failed == 5
        assert len(result.errors) == 2
        assert len(result.checkpoints) == 1

    def test_batch_result_success_rate(self):
        """Test calculating success rate."""
        result = BatchResult(
            total=100,
            successful=80,
            failed=20,
            errors=[],
            checkpoints=[],
        )

        success_rate = result.successful / result.total
        assert success_rate == 0.8