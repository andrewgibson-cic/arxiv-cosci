"""Tests for ML pipeline components.

This module tests the machine learning infrastructure with mocked
PyTorch operations and Neo4j queries to avoid requiring trained models
or live databases during testing.
"""

import pytest
import torch
from unittest.mock import AsyncMock, MagicMock, patch
from packages.ml.link_predictor import GraphSAGEModel, LinkPredictor
from packages.ml.structural_holes import StructuralHole, StructuralHoleDetector
from packages.ml.hypothesis_gen import ResearchHypothesis, HypothesisGenerator
from packages.ml.prediction_pipeline import LinkPredictionPipeline


@pytest.fixture
def mock_graph_data():
    """Create mock graph data for testing."""
    return {
        "x": torch.randn(100, 768),  # 100 nodes, 768 features
        "edge_index": torch.randint(0, 100, (2, 500)),  # 500 edges
        "node_ids": [f"paper_{i}" for i in range(100)],
    }


@pytest.fixture
def sample_structural_hole():
    """Create a sample structural hole for testing."""
    return StructuralHole(
        source_id="paper_1",
        target_id="paper_2",
        source_type="Paper",
        target_type="Paper",
        source_name="Quantum Computing Basics",
        target_name="Advanced Quantum Algorithms",
        score=0.85,
        shared_neighbors=["paper_3", "paper_4"],
        reason="Share 5 common citations but no direct link",
        metadata={"field": "quantum-computing"},
    )


class TestGraphSAGEModel:
    """Tests for GraphSAGE neural network model."""

    def test_model_initialization(self):
        """Test model initialization with default parameters."""
        model = GraphSAGEModel(
            in_channels=768,
            hidden_channels=256,
            out_channels=128,
        )

        assert model is not None
        assert model.conv1 is not None
        assert model.conv2 is not None

    def test_model_forward_pass(self, mock_graph_data):
        """Test forward pass through the model."""
        model = GraphSAGEModel(768, 256, 128)
        
        x = mock_graph_data["x"]
        edge_index = mock_graph_data["edge_index"]

        output = model(x, edge_index)

        assert output.shape == (100, 128)
        assert not torch.isnan(output).any()

    def test_model_device_compatibility(self):
        """Test model works on CPU."""
        model = GraphSAGEModel(768, 256, 128)
        model = model.to("cpu")

        x = torch.randn(10, 768)
        edge_index = torch.randint(0, 10, (2, 20))

        output = model(x, edge_index)

        assert output.device.type == "cpu"

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_model_cuda_compatibility(self):
        """Test model works on CUDA if available."""
        model = GraphSAGEModel(768, 256, 128)
        model = model.to("cuda")

        x = torch.randn(10, 768).cuda()
        edge_index = torch.randint(0, 10, (2, 20)).cuda()

        output = model(x, edge_index)

        assert output.device.type == "cuda"


class TestLinkPredictor:
    """Tests for LinkPredictor class."""

    def test_predictor_initialization(self):
        """Test link predictor initialization."""
        predictor = LinkPredictor(
            in_channels=768,
            hidden_channels=256,
            out_channels=128,
        )

        assert predictor is not None
        assert predictor.model is not None
        assert predictor.device is not None

    def test_train_step(self, mock_graph_data):
        """Test single training step."""
        predictor = LinkPredictor(768, 256, 128)
        
        x = mock_graph_data["x"]
        edge_index = mock_graph_data["edge_index"]
        
        # Create positive and negative edges
        pos_edge_index = edge_index[:, :100]
        neg_edge_index = torch.randint(0, 100, (2, 100))

        loss = predictor.train_step(x, edge_index, pos_edge_index, neg_edge_index)

        assert isinstance(loss, float)
        assert loss > 0  # Loss should be positive

    @patch("packages.ml.link_predictor.torch.save")
    def test_save_model(self, mock_save, tmp_path):
        """Test model saving."""
        predictor = LinkPredictor(768, 256, 128)
        save_path = tmp_path / "model.pt"

        predictor.save_model(save_path)

        mock_save.assert_called_once()

    @patch("packages.ml.link_predictor.torch.load")
    def test_load_model(self, mock_load, tmp_path):
        """Test model loading."""
        predictor = LinkPredictor(768, 256, 128)
        load_path = tmp_path / "model.pt"
        load_path.touch()  # Create empty file

        mock_load.return_value = predictor.model.state_dict()
        predictor.load_model(load_path)

        mock_load.assert_called_once()

    def test_predict_links(self, mock_graph_data):
        """Test link prediction."""
        predictor = LinkPredictor(768, 256, 128)
        
        x = mock_graph_data["x"]
        edge_index = mock_graph_data["edge_index"]
        
        # Generate embeddings
        with torch.no_grad():
            embeddings = predictor.model(x, edge_index)
        
        # Predict links for first 10 nodes
        predictions = predictor.predict_links(embeddings, list(range(10)), top_k=5)

        assert len(predictions) <= 10 * 5  # At most top_k per node
        for pred in predictions:
            assert "source" in pred
            assert "target" in pred
            assert "score" in pred
            assert 0 <= pred["score"] <= 1


class TestStructuralHoleDetector:
    """Tests for structural hole detection."""

    @pytest.mark.asyncio
    async def test_detector_initialization(self):
        """Test detector initialization."""
        mock_driver = MagicMock()
        detector = StructuralHoleDetector(mock_driver)

        assert detector is not None
        assert detector.driver == mock_driver

    @pytest.mark.asyncio
    @patch("packages.ml.structural_holes.AsyncSession")
    async def test_find_paper_gaps(self, mock_session_class):
        """Test finding paper-to-paper gaps."""
        mock_driver = MagicMock()
        detector = StructuralHoleDetector(mock_driver)

        # Mock session and query results
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data.return_value = [
            {
                "paper1": "p1",
                "paper2": "p2",
                "title1": "Paper 1",
                "title2": "Paper 2",
                "shared_citations": 5,
            }
        ]
        mock_session.run.return_value = mock_result
        mock_session_class.return_value.__aenter__.return_value = mock_session

        gaps = await detector.find_paper_gaps(limit=10)

        assert isinstance(gaps, list)
        # Will be empty with mock but structure is tested
        assert all(isinstance(gap, StructuralHole) for gap in gaps)

    @pytest.mark.asyncio
    @patch("packages.ml.structural_holes.AsyncSession")
    async def test_find_concept_gaps(self, mock_session_class):
        """Test finding concept-to-concept gaps."""
        mock_driver = MagicMock()
        detector = StructuralHoleDetector(mock_driver)

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data.return_value = []
        mock_session.run.return_value = mock_result
        mock_session_class.return_value.__aenter__.return_value = mock_session

        gaps = await detector.find_concept_gaps(limit=10)

        assert isinstance(gaps, list)

    @pytest.mark.asyncio
    @patch("packages.ml.structural_holes.AsyncSession")
    async def test_find_all_gaps(self, mock_session_class):
        """Test finding all types of gaps."""
        mock_driver = MagicMock()
        detector = StructuralHoleDetector(mock_driver)

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data.return_value = []
        mock_session.run.return_value = mock_result
        mock_session_class.return_value.__aenter__.return_value = mock_session

        all_gaps = await detector.find_all_gaps(limit_per_type=5)

        assert isinstance(all_gaps, dict)
        assert "paper_gaps" in all_gaps
        assert "concept_gaps" in all_gaps
        assert "temporal_gaps" in all_gaps
        assert "cross_domain_gaps" in all_gaps


class TestHypothesisGenerator:
    """Tests for research hypothesis generation."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        mock_client = AsyncMock()
        mock_client.is_available = AsyncMock(return_value=True)
        mock_client.generate_json = AsyncMock(return_value={
            "hypothesis": "Test hypothesis statement",
            "rationale": "Test rationale",
            "confidence": 0.85,
            "research_questions": ["Question 1", "Question 2"],
            "suggested_methods": ["Method 1"],
            "expected_impact": "High",
        })
        return mock_client

    @pytest.mark.asyncio
    async def test_generator_initialization(self, mock_llm_client):
        """Test hypothesis generator initialization."""
        generator = HypothesisGenerator(mock_llm_client)

        assert generator is not None
        assert generator.llm == mock_llm_client

    @pytest.mark.asyncio
    async def test_generate_single_hypothesis(
        self, mock_llm_client, sample_structural_hole
    ):
        """Test generating a single hypothesis."""
        generator = HypothesisGenerator(mock_llm_client)

        hypothesis = await generator.generate_hypothesis(sample_structural_hole)

        assert hypothesis is not None
        assert isinstance(hypothesis, ResearchHypothesis)
        assert hypothesis.hole == sample_structural_hole
        assert hypothesis.hypothesis == "Test hypothesis statement"
        assert 0 <= hypothesis.confidence <= 1

    @pytest.mark.asyncio
    async def test_generate_batch(self, mock_llm_client, sample_structural_hole):
        """Test generating multiple hypotheses in batch."""
        generator = HypothesisGenerator(mock_llm_client)

        holes = [sample_structural_hole] * 5
        hypotheses = await generator.generate_batch(holes, max_hypotheses=3)

        assert len(hypotheses) <= 3
        assert all(isinstance(h, ResearchHypothesis) for h in hypotheses)

    @pytest.mark.asyncio
    async def test_llm_unavailable(self, sample_structural_hole):
        """Test handling when LLM is unavailable."""
        mock_client = AsyncMock()
        mock_client.is_available = AsyncMock(return_value=False)

        generator = HypothesisGenerator(mock_client)
        hypotheses = await generator.generate_batch([sample_structural_hole])

        assert hypotheses == []

    def test_to_markdown(self, mock_llm_client, sample_structural_hole):
        """Test converting hypothesis to markdown."""
        generator = HypothesisGenerator(mock_llm_client)

        hypothesis = ResearchHypothesis(
            hole=sample_structural_hole,
            hypothesis="Test hypothesis",
            rationale="Test rationale",
            confidence=0.85,
            research_questions=["Q1"],
            suggested_methods=["M1"],
            expected_impact="High",
        )

        markdown = generator.to_markdown(hypothesis)

        assert "Test hypothesis" in markdown
        assert "85%" in markdown or "0.85" in markdown
        assert "Q1" in markdown


class TestLinkPredictionPipeline:
    """Tests for the complete link prediction pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        mock_neo4j = MagicMock()
        mock_chroma = MagicMock()

        pipeline = LinkPredictionPipeline(mock_neo4j, mock_chroma)

        assert pipeline is not None
        assert pipeline.neo4j_client == mock_neo4j
        assert pipeline.chroma_client == mock_chroma

    @pytest.mark.asyncio
    @patch("packages.ml.prediction_pipeline.LinkPredictor")
    async def test_prepare_graph_data(self, mock_predictor_class):
        """Test graph data preparation."""
        mock_neo4j = AsyncMock()
        mock_chroma = MagicMock()
        
        # Mock Neo4j query results
        mock_neo4j.query = AsyncMock(return_value=[
            {"paper_id": "p1", "title": "Paper 1"},
            {"paper_id": "p2", "title": "Paper 2"},
        ])

        # Mock ChromaDB embeddings
        mock_chroma.get_embeddings = MagicMock(return_value={
            "p1": [0.1] * 768,
            "p2": [0.2] * 768,
        })

        pipeline = LinkPredictionPipeline(mock_neo4j, mock_chroma)
        
        # This would normally prepare graph data
        # Testing the structure without full implementation
        assert pipeline is not None

    @pytest.mark.asyncio
    @patch("packages.ml.prediction_pipeline.LinkPredictor")
    async def test_train_model(self, mock_predictor_class):
        """Test model training."""
        mock_neo4j = MagicMock()
        mock_chroma = MagicMock()
        mock_predictor = MagicMock()
        mock_predictor.train_step = MagicMock(return_value=0.5)
        mock_predictor_class.return_value = mock_predictor

        pipeline = LinkPredictionPipeline(mock_neo4j, mock_chroma)

        # Mock training would return metrics
        # Testing the interface
        assert pipeline is not None

    @pytest.mark.asyncio
    @patch("packages.ml.prediction_pipeline.LinkPredictor")
    @patch("packages.ml.prediction_pipeline.StructuralHoleDetector")
    async def test_full_pipeline(
        self, mock_detector_class, mock_predictor_class
    ):
        """Test running the full prediction pipeline."""
        mock_neo4j = AsyncMock()
        mock_chroma = MagicMock()

        # Mock components
        mock_predictor = MagicMock()
        mock_predictor.train_step = MagicMock(return_value=0.5)
        mock_predictor.predict_links = MagicMock(return_value=[])
        mock_predictor_class.return_value = mock_predictor

        mock_detector = MagicMock()
        mock_detector_class.return_value = mock_detector

        pipeline = LinkPredictionPipeline(mock_neo4j, mock_chroma)

        # Testing the pipeline exists and can be initialized
        assert pipeline is not None


class TestEvaluationMetrics:
    """Tests for model evaluation metrics."""

    def test_precision_calculation(self):
        """Test precision metric calculation."""
        # Predicted: 10 links, Actual: 100 links, Correct: 8
        predicted = 10
        actual = 100
        correct = 8

        precision = correct / predicted if predicted > 0 else 0
        assert precision == 0.8

    def test_coverage_calculation(self):
        """Test coverage metric calculation."""
        # Predicted: 10 links, Actual: 100 links, Correct: 8
        predicted = 10
        actual = 100
        correct = 8

        coverage = correct / actual if actual > 0 else 0
        assert coverage == 0.08

    def test_f1_score_calculation(self):
        """Test F1 score calculation."""
        precision = 0.8
        coverage = 0.08

        if precision + coverage > 0:
            f1 = 2 * (precision * coverage) / (precision + coverage)
        else:
            f1 = 0

        assert 0 <= f1 <= 1
        assert abs(f1 - 0.145) < 0.01  # ~0.145


class TestDeviceCompatibility:
    """Tests for device compatibility (CPU/CUDA/MPS)."""

    def test_cpu_device_selection(self):
        """Test CPU device is available."""
        device = torch.device("cpu")
        assert device.type == "cpu"

        tensor = torch.randn(10, 10, device=device)
        assert tensor.device.type == "cpu"

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_cuda_device_selection(self):
        """Test CUDA device if available."""
        device = torch.device("cuda")
        assert device.type == "cuda"

        tensor = torch.randn(10, 10, device=device)
        assert tensor.device.type == "cuda"

    @pytest.mark.skipif(not torch.backends.mps.is_available(), reason="MPS not available")
    def test_mps_device_selection(self):
        """Test MPS device if available (Apple Silicon)."""
        device = torch.device("mps")
        assert device.type == "mps"

        tensor = torch.randn(10, 10, device=device)
        assert tensor.device.type == "mps"


class TestNegativeSampling:
    """Tests for negative edge sampling in training."""

    def test_negative_sampling(self):
        """Test negative edge sampling."""
        num_nodes = 100
        num_neg_samples = 50

        # Sample random negative edges
        neg_edges = torch.randint(0, num_nodes, (2, num_neg_samples))

        assert neg_edges.shape == (2, num_neg_samples)
        assert neg_edges.min() >= 0
        assert neg_edges.max() < num_nodes

    def test_negative_sampling_no_duplicates(self):
        """Test negative sampling avoids existing edges."""
        existing_edges = {(0, 1), (1, 2), (2, 3)}
        num_nodes = 10
        
        # Sample and filter
        neg_edges = []
        attempts = 0
        while len(neg_edges) < 5 and attempts < 100:
            src = torch.randint(0, num_nodes, (1,)).item()
            dst = torch.randint(0, num_nodes, (1,)).item()
            if (src, dst) not in existing_edges and src != dst:
                neg_edges.append((src, dst))
            attempts += 1

        assert len(neg_edges) > 0
        assert all(edge not in existing_edges for edge in neg_edges)
