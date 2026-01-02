"""Tests for AI analysis modules."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date

from packages.ingestion.models import ParsedPaper, Citation, CitationIntent
from packages.ai.ollama_client import OllamaClient
from packages.ai.summarizer import (
    summarize_paper,
    summarize_batch,
    generate_comparative_summary,
    SummaryLevel,
    PaperSummary,
)
from packages.ai.entity_extractor import (
    extract_entities,
    extract_entities_regex,
    extract_key_findings,
    extract_methods_used,
    PaperEntities,
    ExtractedEntity,
)
from packages.ai.citation_classifier import (
    classify_citation,
    classify_citations_batch,
    ClassifiedCitation,
)

# Sample data
@pytest.fixture
def sample_paper():
    return ParsedPaper(
        arxiv_id="2312.12345",
        title="Quantum Computing with Topological Qubits",
        abstract="We present a new method for topological quantum computing using Majorana fermions. Our approach demonstrates 99.9% fidelity.",
        authors=["Alice Smith", "Bob Jones"],
        published_date=date(2023, 12, 25),
        primary_category="quant-ph",
        categories=["quant-ph", "cond-mat"],
        full_text="""
        Section 1: Introduction
        Topological quantum computing is promising.
        
        Section 2: Methods
        We utilize the braiding statistics of Majorana zero modes.
        Equation 1: H = sum(gamma_i * gamma_j)
        
        Section 3: Results
        We achieve 99.9% gate fidelity.
        
        Theorem 1: The braiding is universal.
        
        Einstein field equations are not relevant here.
        The Planck constant is small.
        """,
        citations=[
            Citation(raw_text="[1] Doe et al", arxiv_id="2101.00001", context="As shown in [1], this method is fast."),
            Citation(raw_text="[2] Test et al", doi="10.1234/test", context="However, previous work failed to scale [2]."),
            Citation(raw_text="[3] Smith et al, 2020", context=""),
        ]
    )

# --- OllamaClient Tests ---

@pytest.mark.asyncio
async def test_ollama_client_generate():
    """Test basic text generation."""
    with patch("packages.ai.ollama_client.aiohttp.ClientSession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session_cls.return_value = mock_session
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"response": "Test response"}
        
        # Correctly mock async context manager
        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__.return_value = mock_response
        mock_session.post = MagicMock(return_value=mock_post_ctx)

        client = OllamaClient()
        response = await client.generate("Test prompt")
        
        assert response == "Test response"
        mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_ollama_client_generate_json():
    """Test JSON generation and parsing."""
    with patch("packages.ai.ollama_client.aiohttp.ClientSession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session_cls.return_value = mock_session
        
        mock_response = AsyncMock()
        mock_response.status = 200
        # Mock markdown wrapping which Ollama often does
        mock_response.json.return_value = {"response": "```json\n{\"key\": \"value\"}\n```"}
        
        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__.return_value = mock_response
        mock_session.post = MagicMock(return_value=mock_post_ctx)

        client = OllamaClient()
        result = await client.generate_json("Test prompt")
        
        assert result == {"key": "value"}

# --- Summarizer Tests ---

@pytest.mark.asyncio
async def test_summarize_brief(sample_paper):
    """Test brief summarization."""
    with patch("packages.ai.summarizer.ollama_client.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "A concise summary."
        
        summary = await summarize_paper(sample_paper, SummaryLevel.BRIEF)
        
        assert summary == "A concise summary."
        mock_gen.assert_called_once()
        args, kwargs = mock_gen.call_args
        assert kwargs["max_tokens"] == 100

@pytest.mark.asyncio
async def test_summarize_detailed(sample_paper):
    """Test detailed structured summarization."""
    expected_summary = PaperSummary(
        one_liner="One line.",
        key_contribution="Contribution.",
        methodology="Method.",
        key_findings=["Finding 1", "Finding 2"],
        limitations="Limits.",
        future_work="Future."
    )
    
    with patch("packages.ai.summarizer.ollama_client.generate_structured", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = expected_summary
        
        summary = await summarize_paper(sample_paper, SummaryLevel.DETAILED)
        
        assert isinstance(summary, PaperSummary)
        assert summary.one_liner == "One line."
        assert len(summary.key_findings) == 2

@pytest.mark.asyncio
async def test_summarize_batch(sample_paper):
    """Test batch summarization."""
    with patch("packages.ai.summarizer.summarize_paper", new_callable=AsyncMock) as mock_sum:
        mock_sum.return_value = "Summary"
        
        results = await summarize_batch([sample_paper, sample_paper], SummaryLevel.BRIEF)
        
        assert len(results) == 2
        assert results[0]["summary"] == "Summary"
        assert mock_sum.call_count == 2

# --- Entity Extractor Tests ---

def test_extract_entities_regex(sample_paper):
    """Test regex-based entity extraction."""
    entities = extract_entities_regex(sample_paper)
    
    # Check Theorem extraction (Theorem 1)
    assert any(e.name == "Theorem 1" for e in entities.theorems)
    
    # Check Equation extraction (Equation 1 is likely "Equation 1" in text, but pattern looks for "X equation")
    # "Einstein field equations" matches pattern
    assert any("Einstein field equation" in e.name for e in entities.equations)
    
    # Check Constant extraction
    assert any("Planck constant" in e.name for e in entities.constants)

@pytest.mark.asyncio
async def test_extract_entities_llm_fallback(sample_paper):
    """Test LLM extraction falling back to regex on error."""
    with patch("packages.ai.entity_extractor.ollama_client.generate_structured", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = Exception("LLM failed")
        
        entities = await extract_entities(sample_paper, use_llm=True)
        
        # Should still have regex results
        assert any(e.name == "Theorem 1" for e in entities.theorems)

@pytest.mark.asyncio
async def test_extract_entities_llm_success(sample_paper):
    """Test successful LLM extraction merging with regex."""
    llm_entities = PaperEntities(
        methods=[ExtractedEntity(name="LLM Method", entity_type="method")],
        theorems=[]
    )
    
    with patch("packages.ai.entity_extractor.ollama_client.generate_structured", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = llm_entities
        
        entities = await extract_entities(sample_paper, use_llm=True)
        
        # Should have LLM entity
        assert any(e.name == "LLM Method" for e in entities.methods)
        # Should ALSO have regex entities (Theorem 1)
        assert any(e.name == "Theorem 1" for e in entities.theorems)

@pytest.mark.asyncio
async def test_extract_key_findings(sample_paper):
    """Test key finding extraction."""
    with patch("packages.ai.entity_extractor.ollama_client.generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = ["Finding 1", "Finding 2"]
        
        findings = await extract_key_findings(sample_paper)
        
        assert len(findings) == 2
        assert findings[0] == "Finding 1"

# --- Citation Classifier Tests ---

@pytest.mark.asyncio
async def test_classify_citation(sample_paper):
    """Test single citation classification."""
    with patch("packages.ai.citation_classifier.ollama_client.generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {
            "intent": "METHOD",
            "confidence": 0.9,
            "reasoning": "Uses method"
        }
        
        citation = sample_paper.citations[0]
        classified = await classify_citation(citation)
        
        assert classified.intent == CitationIntent.METHOD
        assert classified.confidence == 0.9

@pytest.mark.asyncio
async def test_classify_citation_no_context(sample_paper):
    """Test citation with no context returns UNKNOWN."""
    citation = sample_paper.citations[2] # No context
    classified = await classify_citation(citation)
    
    assert classified.intent == CitationIntent.UNKNOWN
    assert classified.confidence == 0.0

@pytest.mark.asyncio
async def test_classify_citations_batch(sample_paper):
    """Test batch classification."""
    # Add more citations to trigger batch mode (>3)
    citations = sample_paper.citations + [
        Citation(raw_text="[4] A", arxiv_id="2202.00001", context="C4 context"),
        Citation(raw_text="[5] B", arxiv_id="2202.00002", context="C5 context"),
    ]
    
    # Mock return for the batch call
    batch_response = [
        {"id": "2101.00001", "intent": "METHOD", "confidence": 0.9},
        {"id": "10.1234/test", "intent": "CRITIQUE", "confidence": 0.8},
        {"id": "2202.00001", "intent": "BACKGROUND", "confidence": 0.9},
        {"id": "2202.00002", "intent": "RESULT", "confidence": 0.9},
    ]
    
    with patch("packages.ai.citation_classifier.ollama_client.generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = batch_response
        
        classified = await classify_citations_batch(citations)
        
        # Check first one
        c1 = next(c for c in classified if c.arxiv_id == "2101.00001")
        assert c1.intent == CitationIntent.METHOD
