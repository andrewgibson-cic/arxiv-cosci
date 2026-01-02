"""Paper summarization using local LLM.

Generates summaries at multiple granularities:
- One-line summary (tweet-length)
- Abstract-length summary
- Detailed technical summary
"""

from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from packages.ai.ollama_client import ollama_client
from packages.ingestion.models import ParsedPaper

logger = structlog.get_logger()


class SummaryLevel(str, Enum):
    """Summary granularity levels."""

    BRIEF = "brief"  # 1-2 sentences
    STANDARD = "standard"  # Paragraph
    DETAILED = "detailed"  # Multiple paragraphs with structure


class PaperSummary(BaseModel):
    """Structured paper summary."""

    one_liner: str = Field(..., description="One sentence summary")
    key_contribution: str = Field(..., description="Main contribution in 2-3 sentences")
    methodology: str = Field(..., description="Brief methodology description")
    key_findings: list[str] = Field(default_factory=list, description="List of key findings")
    limitations: str = Field("", description="Noted limitations")
    future_work: str = Field("", description="Suggested future directions")


SYSTEM_PROMPT = """You are a scientific paper analyst specializing in physics and mathematics.
Your task is to summarize research papers accurately and concisely.
Focus on the key contributions, methodology, and findings.
Use precise technical language appropriate for the domain."""


BRIEF_PROMPT = """Summarize this physics/mathematics paper in 1-2 sentences.
Focus on the main contribution and result.

Title: {title}

Abstract: {abstract}

Summary:"""


STANDARD_PROMPT = """Provide a paragraph summary of this physics/mathematics paper.
Include: main objective, methodology, key findings, and significance.

Title: {title}

Abstract: {abstract}

Full text excerpt:
{text_excerpt}

Summary:"""


DETAILED_PROMPT = """Analyze this physics/mathematics paper and provide a structured summary.

Title: {title}

Abstract: {abstract}

Full text (first 3000 chars):
{text_excerpt}

Provide your analysis as JSON with these fields:
- one_liner: One sentence capturing the essence
- key_contribution: Main contribution (2-3 sentences)
- methodology: Brief methodology description
- key_findings: List of 3-5 key findings
- limitations: Any noted limitations
- future_work: Suggested future directions

JSON:"""


async def summarize_paper(
    paper: ParsedPaper,
    level: SummaryLevel = SummaryLevel.STANDARD,
) -> str | PaperSummary:
    """Generate a summary of a paper.

    Args:
        paper: Parsed paper to summarize
        level: Summary granularity level

    Returns:
        String summary for brief/standard, PaperSummary for detailed
    """
    logger.info("summarizing_paper", arxiv_id=paper.arxiv_id, level=level.value)

    if level == SummaryLevel.BRIEF:
        prompt = BRIEF_PROMPT.format(
            title=paper.title,
            abstract=paper.abstract,
        )
        return await ollama_client.generate(
            prompt,
            system=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=100,
        )

    elif level == SummaryLevel.STANDARD:
        text_excerpt = paper.full_text[:2000] if paper.full_text else ""
        prompt = STANDARD_PROMPT.format(
            title=paper.title,
            abstract=paper.abstract,
            text_excerpt=text_excerpt,
        )
        return await ollama_client.generate(
            prompt,
            system=SYSTEM_PROMPT,
            temperature=0.5,
            max_tokens=300,
        )

    else:  # DETAILED
        text_excerpt = paper.full_text[:3000] if paper.full_text else ""
        prompt = DETAILED_PROMPT.format(
            title=paper.title,
            abstract=paper.abstract,
            text_excerpt=text_excerpt,
        )
        return await ollama_client.generate_structured(
            prompt,
            PaperSummary,
            system=SYSTEM_PROMPT,
        )


async def summarize_batch(
    papers: list[ParsedPaper],
    level: SummaryLevel = SummaryLevel.BRIEF,
) -> list[dict[str, Any]]:
    """Summarize multiple papers.

    Args:
        papers: List of papers to summarize
        level: Summary granularity

    Returns:
        List of dicts with arxiv_id and summary
    """
    results = []

    for paper in papers:
        try:
            summary = await summarize_paper(paper, level)
            results.append({
                "arxiv_id": paper.arxiv_id,
                "summary": summary if isinstance(summary, str) else summary.model_dump(),
            })
        except Exception as e:
            logger.error("summarization_failed", arxiv_id=paper.arxiv_id, error=str(e))
            results.append({
                "arxiv_id": paper.arxiv_id,
                "error": str(e),
            })

    return results


async def generate_comparative_summary(
    papers: list[ParsedPaper],
) -> str:
    """Generate a summary comparing multiple papers.

    Args:
        papers: List of 2-5 papers to compare

    Returns:
        Comparative analysis
    """
    if len(papers) < 2:
        raise ValueError("Need at least 2 papers for comparison")

    papers_text = "\n\n".join([
        f"Paper {i+1}: {p.title}\nAbstract: {p.abstract[:500]}"
        for i, p in enumerate(papers[:5])
    ])

    prompt = f"""Compare these physics/mathematics papers:

{papers_text}

Provide a comparative analysis covering:
1. Common themes and connections
2. Key differences in approach
3. How they build on each other
4. Gaps or opportunities for synthesis

Analysis:"""

    return await ollama_client.generate(
        prompt,
        system=SYSTEM_PROMPT,
        temperature=0.6,
        max_tokens=500,
    )
