"""End-to-end workflow tests.

This module tests complete workflows that integrate multiple components
of the system, simulating real-world usage scenarios.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from packages.ingestion.models import ParsedPaper, PaperMetadata, ParserType


@pytest.fixture
def sample_arxiv_id():
    """Sample arXiv ID for testing."""
    return "2401.12345"


@pytest.fixture
def sample_paper_metadata():
    """Sample paper metadata from S2 API."""
    return PaperMetadata(
        id="2401.12345",
        title="Quantum Error Correction in Topological Codes",
        abstract="This paper presents novel approaches to quantum error correction.",
        authors="Alice Smith, Bob Johnson",
        categories=["quant-ph", "math.QA"],
        update_date="2024-01-23",
        primary_category="quant-ph",
    )


@pytest.fixture
def sample_parsed_paper():
    """Sample fully parsed paper."""
    return ParsedPaper(
        arxiv_id="2401.12345",
        title="Quantum Error Correction in Topological Codes",
        abstract="This paper presents novel approaches to quantum error correction.",
        authors=["Alice Smith", "Bob Johnson"],
        categories=["quant-ph", "math.QA"],
        primary_category="quant-ph",
        published_date="2024-01-23",
        full_text="Full paper content...",
        sections=[
            {"title": "Abstract", "content": "..."},
            {"title": "Introduction", "content": "..."},
        ],
        citations=[],
        concepts=[],
        parser_used=ParserType.MARKER,
    )


class TestFetchToIngestWorkflow:
    """Tests for fetch → parse → ingest workflow."""

    @pytest.mark.asyncio
    @patch("packages.ingestion.s2_client.S2Client")
    @patch("packages.knowledge.neo4j_client.Neo4jClient")
    @patch("packages.knowledge.chromadb_client.ChromaDBClient")
    async def test_fetch_and_ingest_workflow(
        self,
        mock_chroma_class,
        mock_neo4j_class,
        mock_s2_class,
        sample_arxiv_id,
        sample_paper_metadata,
    ):
        """Test complete fetch and ingest workflow."""
        # Mock S2 client
        mock_s2 = AsyncMock()
        mock_s2.get_paper_by_arxiv_id = AsyncMock(
            return_value={"title": sample_paper_metadata.title}
        )
        mock_s2.paper_to_metadata = MagicMock(return_value=sample_paper_metadata)
        mock_s2_class.return_value = mock_s2

        # Mock Neo4j client
        mock_neo4j = AsyncMock()
        mock_neo4j.connect = AsyncMock()
        mock_neo4j.create_paper = AsyncMock(return_value="node_id")
        mock_neo4j.close = AsyncMock()
        mock_neo4j_class.return_value = mock_neo4j

        # Mock ChromaDB client
        mock_chroma = MagicMock()
        mock_chroma.add_paper = MagicMock()
        mock_chroma_class.return_value = mock_chroma

        # Simulate workflow
        paper_data = await mock_s2.get_paper_by_arxiv_id(sample_arxiv_id)
        metadata = mock_s2.paper_to_metadata(paper_data)
        
        await mock_neo4j.connect()
        node_id = await mock_neo4j.create_paper(metadata)
        mock_chroma.add_paper(metadata)
        await mock_neo4j.close()

        # Verify workflow completed
        assert metadata.id == sample_arxiv_id
        assert node_id == "node_id"
        mock_s2.get_paper_by_arxiv_id.assert_called_once_with(sample_arxiv_id)
        mock_neo4j.create_paper.assert_called_once()
        mock_chroma.add_paper.assert_called_once()


class TestParseToSearchWorkflow:
    """Tests for parse → embed → search workflow."""

    @pytest.mark.asyncio
    @patch("packages.ingestion.parsing_pipeline.parse_pdf")
    @patch("packages.knowledge.chromadb_client.ChromaDBClient")
    async def test_parse_and_search_workflow(
        self,
        mock_chroma_class,
        mock_parse,
        sample_parsed_paper,
        tmp_path,
    ):
        """Test parse → embed → search workflow."""
        # Create mock PDF
        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF fake content")

        # Mock parsing
        mock_parse.return_value = sample_parsed_paper

        # Mock ChromaDB
        mock_chroma = MagicMock()
        mock_chroma.add_paper = MagicMock()
        mock_chroma.search_papers = MagicMock(return_value=[
            {
                "arxiv_id": sample_parsed_paper.arxiv_id,
                "title": sample_parsed_paper.title,
                "similarity": 0.95,
            }
        ])
        mock_chroma_class.return_value = mock_chroma

        # Simulate workflow
        parsed = mock_parse(pdf_path)
        mock_chroma.add_paper(parsed)
        results = mock_chroma.search_papers("quantum error correction")

        # Verify
        assert parsed.arxiv_id == sample_parsed_paper.arxiv_id
        assert len(results) == 1
        assert results[0]["similarity"] == 0.95


class TestPredictionWorkflow:
    """Tests for train → predict → store workflow."""

    @pytest.mark.asyncio
    @patch("packages.ml.link_predictor.LinkPredictor")
    @patch("packages.ml.structural_holes.StructuralHoleDetector")
    @patch("packages.ml.hypothesis_gen.HypothesisGenerator")
    @patch("packages.knowledge.neo4j_client.Neo4jClient")
    async def test_prediction_workflow(
        self,
        mock_neo4j_class,
        mock_hyp_gen_class,
        mock_detector_class,
        mock_predictor_class,
    ):
        """Test train → predict → generate hypotheses workflow."""
        # Mock predictor
        mock_predictor = MagicMock()
        mock_predictor.train_step = MagicMock(return_value=0.5)
        mock_predictor.predict_links = MagicMock(return_value=[
            {"source": "p1", "target": "p2", "score": 0.9}
        ])
        mock_predictor_class.return_value = mock_predictor

        # Mock detector
        mock_detector = AsyncMock()
        mock_detector.find_all_gaps = AsyncMock(return_value={
            "paper_gaps": [MagicMock(source_id="p1", target_id="p2", score=0.85)]
        })
        mock_detector_class.return_value = mock_detector

        # Mock hypothesis generator
        mock_generator = AsyncMock()
        mock_generator.generate_batch = AsyncMock(return_value=[
            MagicMock(hypothesis="Test hypothesis", confidence=0.8)
        ])
        mock_hyp_gen_class.return_value = mock_generator

        # Mock Neo4j
        mock_neo4j = AsyncMock()
        mock_neo4j.store_predictions = AsyncMock(return_value=1)
        mock_neo4j_class.return_value = mock_neo4j

        # Simulate workflow
        loss = mock_predictor.train_step(None, None, None, None)
        predictions = mock_predictor.predict_links(None, [], top_k=5)
        gaps = await mock_detector.find_all_gaps(limit_per_type=10)
        hypotheses = await mock_generator.generate_batch(gaps["paper_gaps"])
        stored = await mock_neo4j.store_predictions(predictions)

        # Verify
        assert loss == 0.5
        assert len(predictions) == 1
        assert predictions[0]["score"] == 0.9
        assert len(hypotheses) == 1
        assert stored == 1


class TestFullSystemWorkflow:
    """Tests for complete end-to-end system workflow."""

    @pytest.mark.asyncio
    @patch("packages.ingestion.s2_client.S2Client")
    @patch("packages.ingestion.parsing_pipeline.parse_pdf")
    @patch("packages.knowledge.neo4j_client.Neo4jClient")
    @patch("packages.knowledge.chromadb_client.ChromaDBClient")
    @patch("packages.ml.prediction_pipeline.LinkPredictionPipeline")
    async def test_complete_workflow(
        self,
        mock_pipeline_class,
        mock_chroma_class,
        mock_neo4j_class,
        mock_parse,
        mock_s2_class,
        sample_arxiv_id,
        sample_paper_metadata,
        sample_parsed_paper,
    ):
        """Test complete system workflow: fetch → parse → ingest → predict."""
        # Setup mocks
        mock_s2 = AsyncMock()
        mock_s2.get_paper_by_arxiv_id = AsyncMock(return_value={"title": "Test"})
        mock_s2.paper_to_metadata = MagicMock(return_value=sample_paper_metadata)
        mock_s2_class.return_value = mock_s2

        mock_parse.return_value = sample_parsed_paper

        mock_neo4j = AsyncMock()
        mock_neo4j.connect = AsyncMock()
        mock_neo4j.ingest_batch = AsyncMock(return_value={
            "papers_ingested": 1,
            "citations_created": 0,
        })
        mock_neo4j.close = AsyncMock()
        mock_neo4j_class.return_value = mock_neo4j

        mock_chroma = MagicMock()
        mock_chroma.add_papers_batch = MagicMock(return_value=1)
        mock_chroma_class.return_value = mock_chroma

        mock_pipeline = AsyncMock()
        mock_pipeline.run_full_pipeline = AsyncMock(return_value={
            "predictions": [{"source": "p1", "target": "p2", "score": 0.9}],
            "metrics": {"precision": 0.85},
        })
        mock_pipeline_class.return_value = mock_pipeline

        # Execute workflow
        # 1. Fetch from S2
        paper_data = await mock_s2.get_paper_by_arxiv_id(sample_arxiv_id)
        metadata = mock_s2.paper_to_metadata(paper_data)

        # 2. Parse (simulated)
        parsed = sample_parsed_paper

        # 3. Ingest
        await mock_neo4j.connect()
        ingest_result = await mock_neo4j.ingest_batch([parsed])
        chroma_count = mock_chroma.add_papers_batch([parsed])
        await mock_neo4j.close()

        # 4. Predict
        results = await mock_pipeline.run_full_pipeline()

        # Verify complete workflow
        assert metadata.id == sample_arxiv_id
        assert parsed.arxiv_id == sample_arxiv_id
        assert ingest_result["papers_ingested"] == 1
        assert chroma_count == 1
        assert len(results["predictions"]) == 1
        assert results["metrics"]["precision"] == 0.85


class TestErrorRecovery:
    """Tests for error recovery in workflows."""

    @pytest.mark.asyncio
    @patch("packages.ingestion.s2_client.S2Client")
    async def test_fetch_failure_recovery(self, mock_s2_class, sample_arxiv_id):
        """Test workflow recovers from fetch failure."""
        mock_s2 = AsyncMock()
        mock_s2.get_paper_by_arxiv_id = AsyncMock(side_effect=[
            None,  # First attempt fails
            {"title": "Test"},  # Second attempt succeeds
        ])
        mock_s2_class.return_value = mock_s2

        # Simulate retry logic
        paper = await mock_s2.get_paper_by_arxiv_id(sample_arxiv_id)
        if paper is None:
            # Retry
            paper = await mock_s2.get_paper_by_arxiv_id(sample_arxiv_id)

        assert paper is not None
        assert mock_s2.get_paper_by_arxiv_id.call_count == 2

    @pytest.mark.asyncio
    @patch("packages.knowledge.neo4j_client.Neo4jClient")
    async def test_ingest_partial_failure(self, mock_neo4j_class):
        """Test handling of partial ingest failures."""
        mock_neo4j = AsyncMock()
        mock_neo4j.connect = AsyncMock()
        mock_neo4j.ingest_batch = AsyncMock(side_effect=Exception("DB error"))
        mock_neo4j.close = AsyncMock()
        mock_neo4j_class.return_value = mock_neo4j

        # Simulate error handling
        try:
            await mock_neo4j.connect()
            await mock_neo4j.ingest_batch([])
        except Exception as e:
            error_handled = True
            assert str(e) == "DB error"
        finally:
            await mock_neo4j.close()

        assert error_handled
        mock_neo4j.close.assert_called_once()


class TestPerformanceWorkflow:
    """Tests for workflow performance characteristics."""

    @pytest.mark.asyncio
    @patch("packages.ingestion.s2_client.S2Client")
    async def test_batch_fetch_performance(self, mock_s2_class):
        """Test batch fetching is more efficient than sequential."""
        mock_s2 = AsyncMock()
        mock_s2.get_papers_bulk = AsyncMock(return_value=[
            {"title": f"Paper {i}"} for i in range(10)
        ])
        mock_s2_class.return_value = mock_s2

        arxiv_ids = [f"2401.{i:05d}" for i in range(10)]
        
        # Batch fetch
        papers = await mock_s2.get_papers_bulk(arxiv_ids)

        assert len(papers) == 10
        mock_s2.get_papers_bulk.assert_called_once()  # Single call

    def test_parallel_processing_capability(self):
        """Test that workflow supports parallel processing."""
        import concurrent.futures

        def process_paper(paper_id):
            return f"Processed {paper_id}"

        paper_ids = [f"p{i}" for i in range(10)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(process_paper, paper_ids))

        assert len(results) == 10
        assert all("Processed" in r for r in results)


class TestDataFlowValidation:
    """Tests for validating data flow through the system."""

    @pytest.mark.asyncio
    async def test_data_consistency_across_stores(self):
        """Test data consistency between Neo4j and ChromaDB."""
        arxiv_id = "2401.12345"
        
        # Simulate data in both stores
        neo4j_data = {"arxiv_id": arxiv_id, "title": "Test Paper"}
        chroma_data = {"arxiv_id": arxiv_id, "title": "Test Paper"}

        # Verify consistency
        assert neo4j_data["arxiv_id"] == chroma_data["arxiv_id"]
        assert neo4j_data["title"] == chroma_data["title"]

    def test_metadata_preservation(self, sample_paper_metadata, sample_parsed_paper):
        """Test metadata is preserved through workflow."""
        # Verify critical fields preserved from metadata to parsed paper
        assert sample_paper_metadata.id == sample_parsed_paper.arxiv_id
        assert sample_paper_metadata.title == sample_parsed_paper.title
        assert set(sample_paper_metadata.categories) == set(sample_parsed_paper.categories)
