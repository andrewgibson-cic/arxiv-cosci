"""Citation intent classification.

Classifies why a paper cites another paper:
- METHOD: Uses methodology from cited paper
- BACKGROUND: Provides background/context
- RESULT: Compares or builds on results
- CRITIQUE: Critiques or challenges findings
- EXTENSION: Extends the cited work
"""

import structlog
from pydantic import BaseModel, Field

from packages.ai.ollama_client import ollama_client
from packages.ingestion.models import Citation, CitationIntent

logger = structlog.get_logger()


class ClassifiedCitation(BaseModel):
    """A citation with classified intent."""

    arxiv_id: str | None = None
    doi: str | None = None
    intent: CitationIntent
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    reasoning: str = Field("", description="Brief explanation of classification")


SYSTEM_PROMPT = """You are an expert at analyzing scientific citations.
Your task is to classify why one paper cites another based on the context.
Be precise and base your classification only on the evidence provided."""


CLASSIFICATION_PROMPT = """Classify the intent of this citation in a physics/mathematics paper.

Citation context: "{context}"

The cited paper ID is: {cited_id}

Classification options:
- METHOD: The citing paper uses methodology, techniques, or algorithms from the cited paper
- BACKGROUND: The citation provides background information or establishes context
- RESULT: The citing paper compares to, builds on, or discusses results from the cited paper
- CRITIQUE: The citing paper critiques, challenges, or refutes claims from the cited paper
- EXTENSION: The citing paper directly extends or generalizes the cited work

Output JSON:
{{
  "intent": "METHOD|BACKGROUND|RESULT|CRITIQUE|EXTENSION",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}

JSON:"""


BATCH_CLASSIFICATION_PROMPT = """Classify the intent of these citations in a physics/mathematics paper.

{citations_text}

For each citation, classify as:
- METHOD: Uses methodology from cited paper
- BACKGROUND: Provides background/context
- RESULT: Compares or builds on results
- CRITIQUE: Critiques or challenges
- EXTENSION: Extends the work

Output JSON array:
[
  {{"id": "cited_paper_id", "intent": "...", "confidence": 0.0-1.0, "reasoning": "..."}}
]

JSON:"""


async def classify_citation(citation: Citation) -> ClassifiedCitation:
    """Classify the intent of a single citation.

    Args:
        citation: Citation with context

    Returns:
        ClassifiedCitation with intent
    """
    if not citation.context:
        return ClassifiedCitation(
            arxiv_id=citation.arxiv_id,
            doi=citation.doi,
            intent=CitationIntent.UNKNOWN,
            confidence=0.0,
            reasoning="No context available",
        )

    cited_id = citation.arxiv_id or citation.doi or "unknown"

    prompt = CLASSIFICATION_PROMPT.format(
        context=citation.context[:500],
        cited_id=cited_id,
    )

    try:
        result = await ollama_client.generate_json(
            prompt,
            system=SYSTEM_PROMPT,
            temperature=0.3,
        )

        intent_str = result.get("intent", "UNKNOWN").upper()
        try:
            intent = CitationIntent(intent_str.lower())
        except ValueError:
            intent = CitationIntent.UNKNOWN

        return ClassifiedCitation(
            arxiv_id=citation.arxiv_id,
            doi=citation.doi,
            intent=intent,
            confidence=result.get("confidence", 0.7),
            reasoning=result.get("reasoning", ""),
        )

    except Exception as e:
        logger.warning("classification_failed", error=str(e))
        return ClassifiedCitation(
            arxiv_id=citation.arxiv_id,
            doi=citation.doi,
            intent=CitationIntent.UNKNOWN,
            confidence=0.0,
            reasoning=f"Classification error: {str(e)}",
        )


async def classify_citations_batch(
    citations: list[Citation],
) -> list[ClassifiedCitation]:
    """Classify multiple citations in batch.

    Args:
        citations: List of citations with context

    Returns:
        List of classified citations
    """
    # Filter citations with context
    valid_citations = [c for c in citations if c.context]

    if not valid_citations:
        return [
            ClassifiedCitation(
                arxiv_id=c.arxiv_id,
                doi=c.doi,
                intent=CitationIntent.UNKNOWN,
                confidence=0.0,
            )
            for c in citations
        ]

    # For small batches, process individually
    if len(valid_citations) <= 3:
        results = []
        for c in citations:
            if c.context:
                results.append(await classify_citation(c))
            else:
                results.append(ClassifiedCitation(
                    arxiv_id=c.arxiv_id,
                    doi=c.doi,
                    intent=CitationIntent.UNKNOWN,
                    confidence=0.0,
                ))
        return results

    # Batch processing for larger sets
    citations_text = "\n\n".join([
        f"Citation {i+1} (ID: {c.arxiv_id or c.doi or 'unknown'}):\n\"{c.context[:300]}\""
        for i, c in enumerate(valid_citations[:10])  # Limit to 10
    ])

    prompt = BATCH_CLASSIFICATION_PROMPT.format(citations_text=citations_text)

    try:
        results = await ollama_client.generate_json(
            prompt,
            system=SYSTEM_PROMPT,
            temperature=0.3,
        )

        if not isinstance(results, list):
            results = results.get("citations", [])

        # Map results back to original citations
        result_map: dict[str, dict] = {}
        for r in results:
            rid = r.get("id", "")
            result_map[rid] = r

        classified = []
        for c in citations:
            cid = c.arxiv_id or c.doi or ""
            if cid in result_map:
                r = result_map[cid]
                intent_str = r.get("intent", "UNKNOWN").upper()
                try:
                    intent = CitationIntent(intent_str.lower())
                except ValueError:
                    intent = CitationIntent.UNKNOWN

                classified.append(ClassifiedCitation(
                    arxiv_id=c.arxiv_id,
                    doi=c.doi,
                    intent=intent,
                    confidence=r.get("confidence", 0.7),
                    reasoning=r.get("reasoning", ""),
                ))
            else:
                classified.append(ClassifiedCitation(
                    arxiv_id=c.arxiv_id,
                    doi=c.doi,
                    intent=CitationIntent.UNKNOWN,
                    confidence=0.0,
                ))

        return classified

    except Exception as e:
        logger.error("batch_classification_failed", error=str(e))
        # Fall back to individual classification
        return [await classify_citation(c) for c in citations]


def get_citation_intent_distribution(
    classified: list[ClassifiedCitation],
) -> dict[str, int]:
    """Get distribution of citation intents.

    Args:
        classified: List of classified citations

    Returns:
        Dict mapping intent to count
    """
    distribution: dict[str, int] = {}
    for c in classified:
        intent = c.intent.value
        distribution[intent] = distribution.get(intent, 0) + 1
    return distribution
