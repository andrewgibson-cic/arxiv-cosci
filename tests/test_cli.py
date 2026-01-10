"""Tests for CLI commands.

This module tests all Click CLI commands with mocked dependencies
to avoid requiring external services during testing.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from apps.cli.main import app
from packages.ingestion.models import ParsedPaper, PaperMetadata


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_metadata():
    """Sample paper metadata for testing."""
    return PaperMetadata(
        id="2401.12345",
        title="Test Paper",
        abstract="This is a test abstract.",
        authors="Author One, Author Two",
        categories=["quant-ph", "math.QA"],
        update_date="2024-01-23",
        primary_category="quant-ph",
    )


@pytest.fixture
def sample_parsed_paper():
    """Sample parsed paper for testing."""
    return ParsedPaper(
        arxiv_id="2401.12345",
        title="Test Paper",
        abstract="This is a test abstract.",
        authors=["Author One", "Author Two"],
        categories=["quant-ph"],
        primary_category="quant-ph",
        published_date="2024-01-23",
        full_text="Test content",
        sections=[],
        citations=[],
        concepts=[],
    )


class TestFetchCommand:
    """Tests for the 'fetch' command."""

    @patch("apps.cli.main.S2Client")
    @pytest.mark.asyncio
    async def test_fetch_single_paper(self, mock_s2_client, cli_runner, sample_metadata):
        """Test fetching a single paper."""
        # Setup mock
        mock_instance = AsyncMock()
        mock_instance.get_paper_by_arxiv_id = AsyncMock(return_value={"title": "Test"})
        mock_instance.paper_to_metadata = MagicMock(return_value=sample_metadata)
        mock_s2_client.return_value = mock_instance

        result = cli_runner.invoke(app, ["fetch", "2401.12345"])

        assert result.exit_code == 0
        assert "2401.12345" in result.output or "Test Paper" in result.output

    @patch("apps.cli.main.S2Client")
    @pytest.mark.asyncio
    async def test_fetch_with_output_file(
        self, mock_s2_client, cli_runner, sample_metadata, tmp_path
    ):
        """Test fetching papers with JSON output."""
        output_file = tmp_path / "papers.json"

        # Setup mock
        mock_instance = AsyncMock()
        mock_instance.get_paper_by_arxiv_id = AsyncMock(return_value={"title": "Test"})
        mock_instance.paper_to_metadata = MagicMock(return_value=sample_metadata)
        mock_s2_client.return_value = mock_instance

        result = cli_runner.invoke(
            app, ["fetch", "2401.12345", "--output", str(output_file)]
        )

        assert result.exit_code == 0
        # Note: The actual file write happens in async context, so we check the command ran

    @patch("apps.cli.main.S2Client")
    @pytest.mark.asyncio
    async def test_fetch_multiple_papers(self, mock_s2_client, cli_runner, sample_metadata):
        """Test fetching multiple papers."""
        mock_instance = AsyncMock()
        mock_instance.get_paper_by_arxiv_id = AsyncMock(return_value={"title": "Test"})
        mock_instance.paper_to_metadata = MagicMock(return_value=sample_metadata)
        mock_s2_client.return_value = mock_instance

        result = cli_runner.invoke(app, ["fetch", "2401.12345", "2402.13579"])

        assert result.exit_code == 0


class TestStatsCommand:
    """Tests for the 'stats' command."""

    def test_stats_command(self, cli_runner, tmp_path):
        """Test stats command with mock data file."""
        # Create a mock metadata file
        metadata_file = tmp_path / "metadata.json"
        test_data = [
            {"id": "1", "categories": "quant-ph"},
            {"id": "2", "categories": "quant-ph math.QA"},
        ]
        metadata_file.write_text("\n".join(json.dumps(d) for d in test_data))

        with patch("apps.cli.main.get_category_counts") as mock_counts:
            mock_counts.return_value = {"quant-ph": 2, "math.QA": 1}
            result = cli_runner.invoke(app, ["stats", str(metadata_file)])

            assert result.exit_code == 0
            assert "quant-ph" in result.output


class TestCheckCommand:
    """Tests for the 'check' command."""

    def test_check_command(self, cli_runner):
        """Test system check command."""
        result = cli_runner.invoke(app, ["check"])

        assert result.exit_code == 0
        assert "Python" in result.output
        assert "OK" in result.output or "MISSING" in result.output


class TestInitDbCommand:
    """Tests for the 'init-db' command."""

    @patch("apps.cli.main.neo4j_client")
    @pytest.mark.asyncio
    async def test_init_db_success(self, mock_neo4j, cli_runner):
        """Test successful database initialization."""
        mock_neo4j.init_schema = AsyncMock()
        mock_neo4j.close = AsyncMock()

        result = cli_runner.invoke(app, ["init-db"])

        assert result.exit_code == 0
        assert "Initializing" in result.output or "Schema" in result.output

    @patch("apps.cli.main.neo4j_client")
    @pytest.mark.asyncio
    async def test_init_db_failure(self, mock_neo4j, cli_runner):
        """Test database initialization failure."""
        mock_neo4j.init_schema = AsyncMock(side_effect=Exception("Connection failed"))
        mock_neo4j.close = AsyncMock()

        result = cli_runner.invoke(app, ["init-db"])

        # Command should handle the error gracefully
        assert "Failed" in result.output or "Error" in result.output or "Ensure" in result.output


class TestSearchCommand:
    """Tests for the 'search' command."""

    @patch("apps.cli.main.chromadb_client")
    def test_search_with_results(self, mock_chroma, cli_runner):
        """Test search command with results."""
        mock_chroma.search_papers = MagicMock(
            return_value=[
                {
                    "arxiv_id": "2401.12345",
                    "title": "Test Paper",
                    "primary_category": "quant-ph",
                    "similarity": 0.95,
                }
            ]
        )

        result = cli_runner.invoke(app, ["search", "quantum error correction"])

        assert result.exit_code == 0
        assert "Search" in result.output or "2401.12345" in result.output

    @patch("apps.cli.main.chromadb_client")
    def test_search_no_results(self, mock_chroma, cli_runner):
        """Test search command with no results."""
        mock_chroma.search_papers = MagicMock(return_value=[])

        result = cli_runner.invoke(app, ["search", "nonexistent topic"])

        assert result.exit_code == 0
        assert "No results" in result.output or "found" in result.output


class TestSummarizeCommand:
    """Tests for the 'summarize' command."""

    @patch("apps.cli.main.get_llm_client")
    @patch("apps.cli.main.close_client")
    @patch("apps.cli.main.summarize_paper")
    @pytest.mark.asyncio
    async def test_summarize_brief(
        self,
        mock_summarize,
        mock_close,
        mock_get_llm,
        cli_runner,
        tmp_path,
        sample_parsed_paper,
    ):
        """Test brief summarization."""
        # Create paper file
        paper_file = tmp_path / "2401.12345.json"
        paper_file.write_text(sample_parsed_paper.model_dump_json())

        # Setup mocks
        mock_llm = AsyncMock()
        mock_llm.is_available = AsyncMock(return_value=True)
        mock_get_llm.return_value = mock_llm
        mock_summarize.return_value = "Brief summary of the paper."
        mock_close.return_value = AsyncMock()

        result = cli_runner.invoke(app, ["summarize", str(paper_file), "--level", "brief"])

        assert result.exit_code == 0

    def test_summarize_paper_not_found(self, cli_runner):
        """Test summarize with non-existent paper."""
        result = cli_runner.invoke(app, ["summarize", "nonexistent.json"])

        assert result.exit_code == 0
        assert "not found" in result.output


class TestExtractCommand:
    """Tests for the 'extract' command."""

    @patch("apps.cli.main.extract_entities_regex")
    @pytest.mark.asyncio
    async def test_extract_regex_only(
        self, mock_extract, cli_runner, tmp_path, sample_parsed_paper
    ):
        """Test entity extraction with regex only."""
        paper_file = tmp_path / "2401.12345.json"
        paper_file.write_text(sample_parsed_paper.model_dump_json())

        from packages.ingestion.models import ExtractedEntities, NamedEntity

        mock_extract.return_value = ExtractedEntities(
            methods=[NamedEntity(name="Test Method", confidence=1.0)],
            theorems=[],
            equations=[],
            constants=[],
            datasets=[],
            conjectures=[],
        )

        result = cli_runner.invoke(app, ["extract", str(paper_file), "--no-llm"])

        assert result.exit_code == 0


class TestAiCheckCommand:
    """Tests for the 'ai-check' command."""

    @patch("apps.cli.main.get_llm_client")
    @patch("apps.cli.main.close_client")
    @pytest.mark.asyncio
    async def test_ai_check_available(self, mock_close, mock_get_llm, cli_runner):
        """Test AI check when service is available."""
        mock_llm = AsyncMock()
        mock_llm.is_available = AsyncMock(return_value=True)
        mock_get_llm.return_value = mock_llm
        mock_close.return_value = AsyncMock()

        result = cli_runner.invoke(app, ["ai-check"])

        assert result.exit_code == 0
        assert "Status" in result.output or "AI" in result.output


class TestDbStatsCommand:
    """Tests for the 'db-stats' command."""

    @patch("apps.cli.main.neo4j_client")
    @patch("apps.cli.main.chromadb_client")
    @pytest.mark.asyncio
    async def test_db_stats(self, mock_chroma, mock_neo4j, cli_runner):
        """Test database statistics command."""
        mock_chroma.get_stats = MagicMock(return_value={"papers": 5, "concepts": 10})
        mock_neo4j.connect = AsyncMock()
        mock_neo4j.get_stats = AsyncMock(
            return_value={"papers": 5, "authors": 3, "citations": 12}
        )
        mock_neo4j.close = AsyncMock()

        result = cli_runner.invoke(app, ["db-stats"])

        assert result.exit_code == 0
        assert "Database" in result.output or "Statistics" in result.output


class TestIngestCommand:
    """Tests for the 'ingest' command."""

    @patch("apps.cli.main.neo4j_client")
    @patch("apps.cli.main.chromadb_client")
    @pytest.mark.asyncio
    async def test_ingest_to_both(
        self, mock_chroma, mock_neo4j, cli_runner, tmp_path, sample_parsed_paper
    ):
        """Test ingesting to both Neo4j and ChromaDB."""
        # Create test data directory
        data_dir = tmp_path / "processed"
        data_dir.mkdir()
        paper_file = data_dir / "2401.12345.json"
        paper_file.write_text(sample_parsed_paper.model_dump_json())

        # Setup mocks
        mock_neo4j.connect = AsyncMock()
        mock_neo4j.ingest_batch = AsyncMock(
            return_value={"papers_ingested": 1, "citations_created": 0}
        )
        mock_neo4j.close = AsyncMock()
        mock_chroma.add_papers_batch = MagicMock(return_value=1)

        result = cli_runner.invoke(app, ["ingest", "--input", str(data_dir)])

        assert result.exit_code == 0

    def test_ingest_no_files(self, cli_runner, tmp_path):
        """Test ingest with no JSON files."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = cli_runner.invoke(app, ["ingest", "--input", str(empty_dir)])

        assert result.exit_code == 0
        assert "No JSON files" in result.output or "found" in result.output


class TestTrainPredictorCommand:
    """Tests for the 'train-predictor' command."""

    @patch("apps.cli.main.LinkPredictionPipeline")
    @patch("apps.cli.main.neo4j_client")
    @patch("apps.cli.main.chromadb_client")
    @pytest.mark.asyncio
    async def test_train_predictor(
        self, mock_chroma, mock_neo4j, mock_pipeline_class, cli_runner, tmp_path
    ):
        """Test training link predictor."""
        mock_neo4j.connect = AsyncMock()
        mock_neo4j.close = AsyncMock()

        mock_pipeline = AsyncMock()
        mock_pipeline.run_full_pipeline = AsyncMock(
            return_value={
                "graph_stats": {"num_nodes": 100, "num_edges": 200},
                "predictions": [{"score": 0.9}] * 10,
                "metrics": {"precision": 0.85, "coverage": 0.75},
                "stored_count": 10,
            }
        )
        mock_pipeline_class.return_value = mock_pipeline

        result = cli_runner.invoke(
            app,
            [
                "train-predictor",
                "--node-limit",
                "100",
                "--epochs",
                "10",
                "--checkpoint-dir",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0


class TestFindGapsCommand:
    """Tests for the 'find-gaps' command."""

    @patch("apps.cli.main.StructuralHoleDetector")
    @patch("apps.cli.main.neo4j_client")
    @pytest.mark.asyncio
    async def test_find_gaps_all_types(
        self, mock_neo4j, mock_detector_class, cli_runner
    ):
        """Test finding all types of gaps."""
        mock_neo4j.connect = AsyncMock()
        mock_neo4j.close = AsyncMock()
        mock_neo4j.driver = MagicMock()

        from packages.ml.structural_holes import StructuralHole

        mock_detector = AsyncMock()
        mock_detector.find_all_gaps = AsyncMock(
            return_value={
                "paper_gaps": [
                    StructuralHole(
                        source_id="1",
                        target_id="2",
                        source_type="Paper",
                        target_type="Paper",
                        source_name="Paper A",
                        target_name="Paper B",
                        score=0.85,
                        shared_neighbors=["3"],
                        reason="Shared 5 citations",
                    )
                ],
                "concept_gaps": [],
            }
        )
        mock_detector_class.return_value = mock_detector

        result = cli_runner.invoke(app, ["find-gaps", "--type", "all", "--limit", "10"])

        assert result.exit_code == 0

    @patch("apps.cli.main.StructuralHoleDetector")
    @patch("apps.cli.main.neo4j_client")
    @pytest.mark.asyncio
    async def test_find_gaps_with_output(
        self, mock_neo4j, mock_detector_class, cli_runner, tmp_path
    ):
        """Test finding gaps with JSON output."""
        output_file = tmp_path / "gaps.json"

        mock_neo4j.connect = AsyncMock()
        mock_neo4j.close = AsyncMock()
        mock_neo4j.driver = MagicMock()

        from packages.ml.structural_holes import StructuralHole

        mock_detector = AsyncMock()
        mock_detector.find_all_gaps = AsyncMock(
            return_value={
                "paper_gaps": [
                    StructuralHole(
                        source_id="1",
                        target_id="2",
                        source_type="Paper",
                        target_type="Paper",
                        source_name="Paper A",
                        target_name="Paper B",
                        score=0.85,
                        shared_neighbors=["3"],
                        reason="Test",
                    )
                ]
            }
        )
        mock_detector_class.return_value = mock_detector

        result = cli_runner.invoke(
            app, ["find-gaps", "--output", str(output_file)]
        )

        assert result.exit_code == 0


class TestGenerateHypothesesCommand:
    """Tests for the 'generate-hypotheses' command."""

    @patch("apps.cli.main.HypothesisGenerator")
    @patch("apps.cli.main.get_llm_client")
    @patch("apps.cli.main.close_client")
    @patch("apps.cli.main.neo4j_client")
    @pytest.mark.asyncio
    async def test_generate_hypotheses(
        self,
        mock_neo4j,
        mock_close,
        mock_get_llm,
        mock_generator_class,
        cli_runner,
        tmp_path,
    ):
        """Test hypothesis generation."""
        output_file = tmp_path / "hypotheses.md"

        # Setup LLM mock
        mock_llm = AsyncMock()
        mock_llm.is_available = AsyncMock(return_value=True)
        mock_get_llm.return_value = mock_llm
        mock_close.return_value = AsyncMock()

        # Setup hypothesis generator mock
        from packages.ml.hypothesis_gen import ResearchHypothesis
        from packages.ml.structural_holes import StructuralHole

        test_hole = StructuralHole(
            source_id="1",
            target_id="2",
            source_type="Paper",
            target_type="Paper",
            source_name="Paper A",
            target_name="Paper B",
            score=0.85,
            shared_neighbors=[],
            reason="Test gap",
        )

        test_hypothesis = ResearchHypothesis(
            hole=test_hole,
            hypothesis="Test hypothesis",
            rationale="Test rationale",
            confidence=0.8,
            research_questions=["Q1"],
            suggested_methods=["M1"],
            expected_impact="High",
        )

        mock_generator = AsyncMock()
        mock_generator.generate_batch = AsyncMock(return_value=[test_hypothesis])
        mock_generator.to_markdown = MagicMock(return_value="# Test")
        mock_generator_class.return_value = mock_generator

        # Create gaps file
        gaps_file = tmp_path / "gaps.json"
        gaps_data = {
            "paper_gaps": [
                {
                    "source_id": "1",
                    "target_id": "2",
                    "source_name": "Paper A",
                    "target_name": "Paper B",
                    "score": 0.85,
                    "reason": "Test",
                    "shared_neighbors": [],
                    "metadata": {},
                }
            ]
        }
        gaps_file.write_text(json.dumps(gaps_data))

        result = cli_runner.invoke(
            app,
            [
                "generate-hypotheses",
                "--gaps-file",
                str(gaps_file),
                "--max",
                "5",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0


class TestParseCommand:
    """Tests for the 'parse' command."""

    @patch("apps.cli.main.parse_pdf_file")
    def test_parse_pdfs(self, mock_parse, cli_runner, tmp_path, sample_parsed_paper):
        """Test parsing PDF files."""
        # Create test PDF directory
        input_dir = tmp_path / "pdfs"
        input_dir.mkdir()
        pdf_file = input_dir / "test.pdf"
        pdf_file.write_text("fake pdf content")

        output_dir = tmp_path / "output"

        mock_parse.return_value = sample_parsed_paper

        result = cli_runner.invoke(
            app,
            ["parse", "--input", str(input_dir), "--output", str(output_dir), "--limit", "1"],
        )

        assert result.exit_code == 0


class TestDownloadCommand:
    """Tests for the 'download' command."""

    @patch("apps.cli.main.download_papers")
    @patch("apps.cli.main.stream_kaggle_metadata")
    def test_download_papers(
        self, mock_stream, mock_download, cli_runner, tmp_path
    ):
        """Test downloading papers."""
        # Create test metadata file
        metadata_file = tmp_path / "metadata.json"
        test_data = {"id": "2401.12345", "categories": ["quant-ph"]}
        metadata_file.write_text(json.dumps(test_data))

        # Setup mocks
        from packages.ingestion.models import ArxivPaper

        mock_stream.return_value = iter(
            [
                ArxivPaper(
                    id="2401.12345",
                    title="Test",
                    abstract="Test",
                    categories="quant-ph",
                    authors="Author",
                    versions=[],
                )
            ]
        )
        mock_download.return_value = AsyncMock(return_value=["2401.12345.pdf"])

        result = cli_runner.invoke(
            app,
            [
                "download",
                str(metadata_file),
                "--limit",
                "1",
                "--output",
                str(tmp_path / "pdfs"),
            ],
        )

        assert result.exit_code == 0


class TestSubsetCommand:
    """Tests for the 'subset' command."""

    @patch("apps.cli.main.create_subset")
    def test_create_subset(self, mock_create, cli_runner, tmp_path):
        """Test creating a metadata subset."""
        metadata_file = tmp_path / "metadata.json"
        metadata_file.write_text('{"id": "1", "categories": "quant-ph"}')

        output_file = tmp_path / "subset.json"

        mock_create.return_value = 1

        result = cli_runner.invoke(
            app,
            [
                "subset",
                str(metadata_file),
                "--output",
                str(output_file),
                "--limit",
                "10",
            ],
        )

        assert result.exit_code == 0
        assert "Created subset" in result.output or "1" in result.output
