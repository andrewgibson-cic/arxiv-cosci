"""AI/LLM package for paper analysis.

This package handles:
- Paper summarization
- Entity extraction
- Citation intent classification
- Hypothesis generation
"""

from packages.ai.ollama_client import OllamaClient, ollama_client
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
    get_citation_intent_distribution,
    ClassifiedCitation,
)

__all__ = [
    # Client
    "OllamaClient",
    "ollama_client",
    # Summarization
    "summarize_paper",
    "summarize_batch",
    "generate_comparative_summary",
    "SummaryLevel",
    "PaperSummary",
    # Entity extraction
    "extract_entities",
    "extract_entities_regex",
    "extract_key_findings",
    "extract_methods_used",
    "PaperEntities",
    "ExtractedEntity",
    # Citation classification
    "classify_citation",
    "classify_citations_batch",
    "get_citation_intent_distribution",
    "ClassifiedCitation",
]
