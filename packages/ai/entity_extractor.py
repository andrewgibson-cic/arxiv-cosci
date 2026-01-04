"""Entity extraction from physics/math papers.

Extracts domain-specific entities:
- Methods and techniques
- Theorems and lemmas
- Equations and formulas
- Physical constants
- Datasets
- Conjectures
"""

import re
from typing import Any

import structlog
from pydantic import BaseModel, Field

from packages.ai.factory import get_llm_client
from packages.ingestion.models import ConceptType, ParsedPaper

logger = structlog.get_logger()


class ExtractedEntity(BaseModel):
    """An entity extracted from a paper."""

    name: str = Field(..., description="Entity name")
    entity_type: str = Field(..., description="Type of entity")
    context: str = Field("", description="Surrounding context")
    confidence: float = Field(0.8, ge=0.0, le=1.0, description="Extraction confidence")


class PaperEntities(BaseModel):
    """All entities extracted from a paper."""

    methods: list[ExtractedEntity] = Field(default_factory=list)
    theorems: list[ExtractedEntity] = Field(default_factory=list)
    equations: list[ExtractedEntity] = Field(default_factory=list)
    constants: list[ExtractedEntity] = Field(default_factory=list)
    datasets: list[ExtractedEntity] = Field(default_factory=list)
    conjectures: list[ExtractedEntity] = Field(default_factory=list)


SYSTEM_PROMPT = """You are an expert in physics and mathematics research.
Your task is to identify and extract key scientific entities from papers.
Be precise and only extract entities that are clearly present in the text."""


ENTITY_EXTRACTION_PROMPT = """Extract scientific entities from this physics/mathematics paper.

Title: {title}

Abstract: {abstract}

Text excerpt:
{text_excerpt}

Extract entities in these categories:
1. Methods/Techniques (algorithms, procedures, mathematical methods)
2. Theorems/Lemmas (named theorems, proven statements)
3. Named Equations (famous equations like Schrödinger, Einstein field, etc.)
4. Physical Constants (Planck, fine structure, etc.)
5. Datasets (if any experimental data is mentioned)
6. Conjectures (unproven hypotheses)

Output as JSON:
{{
  "methods": [
    {{"name": "...", "entity_type": "method", "context": "brief context", "confidence": 0.9}}
  ],
  "theorems": [...],
  "equations": [...],
  "constants": [...],
  "datasets": [...],
  "conjectures": [...]
}}

Only include entities you are confident about. JSON:"""


# Regex patterns for common physics/math entities
THEOREM_PATTERN = re.compile(
    r"(?:Theorem|Lemma|Proposition|Corollary)\s+(\d+(?:\.\d+)*)",
    re.IGNORECASE,
)

NAMED_THEOREM_PATTERN = re.compile(
    r"(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:theorem|lemma|conjecture)",
    re.IGNORECASE,
)

EQUATION_PATTERN = re.compile(
    r"(?:the\s+)?([A-Z][a-z]+(?:[-\s][A-Z][a-z]+)*)\s+equation",
    re.IGNORECASE,
)

CONSTANT_PATTERN = re.compile(
    r"(?:Planck|Boltzmann|fine[- ]structure|gravitational|cosmological)\s+constant",
    re.IGNORECASE,
)


def extract_entities_regex(paper: ParsedPaper) -> PaperEntities:
    """Extract entities using regex patterns (fast, no LLM).

    Args:
        paper: Parsed paper

    Returns:
        Extracted entities
    """
    text = f"{paper.title} {paper.abstract} {paper.full_text[:5000]}"

    entities = PaperEntities()

    # Extract theorems
    for match in THEOREM_PATTERN.finditer(text):
        entities.theorems.append(ExtractedEntity(
            name=f"Theorem {match.group(1)}",
            entity_type="theorem",
            context=text[max(0, match.start()-50):match.end()+50],
            confidence=0.9,
        ))

    for match in NAMED_THEOREM_PATTERN.finditer(text):
        entities.theorems.append(ExtractedEntity(
            name=f"{match.group(1)} theorem",
            entity_type="theorem",
            context=text[max(0, match.start()-50):match.end()+50],
            confidence=0.85,
        ))

    # Extract named equations
    for match in EQUATION_PATTERN.finditer(text):
        entities.equations.append(ExtractedEntity(
            name=f"{match.group(1)} equation",
            entity_type="equation",
            context=text[max(0, match.start()-50):match.end()+50],
            confidence=0.85,
        ))

    # Extract constants
    for match in CONSTANT_PATTERN.finditer(text):
        entities.constants.append(ExtractedEntity(
            name=match.group(0),
            entity_type="constant",
            context=text[max(0, match.start()-50):match.end()+50],
            confidence=0.9,
        ))

    return entities


async def extract_entities_llm(paper: ParsedPaper) -> PaperEntities:
    """Extract entities using LLM (comprehensive, slower).

    Args:
        paper: Parsed paper

    Returns:
        Extracted entities
    """
    logger.info("extracting_entities", arxiv_id=paper.arxiv_id)

    text_excerpt = paper.full_text[:3000] if paper.full_text else ""

    prompt = ENTITY_EXTRACTION_PROMPT.format(
        title=paper.title,
        abstract=paper.abstract,
        text_excerpt=text_excerpt,
    )

    try:
        return await get_llm_client().generate_structured(
            prompt,
            PaperEntities,
            system=SYSTEM_PROMPT,
        )
    except Exception as e:
        logger.warning("llm_extraction_failed", error=str(e))
        # Fall back to regex
        return extract_entities_regex(paper)


async def extract_entities(
    paper: ParsedPaper,
    use_llm: bool = True,
) -> PaperEntities:
    """Extract entities from a paper.

    Args:
        paper: Parsed paper
        use_llm: Whether to use LLM (slower but more comprehensive)

    Returns:
        Extracted entities
    """
    if use_llm:
        llm_entities = await extract_entities_llm(paper)
        # Merge with regex for higher recall
        regex_entities = extract_entities_regex(paper)

        # Deduplicate by name
        seen_names: set[str] = set()
        merged = PaperEntities()

        for category in ["methods", "theorems", "equations", "constants", "datasets", "conjectures"]:
            all_entities = getattr(llm_entities, category) + getattr(regex_entities, category)
            unique = []
            for e in all_entities:
                if e.name.lower() not in seen_names:
                    seen_names.add(e.name.lower())
                    unique.append(e)
            setattr(merged, category, unique)

        return merged

    return extract_entities_regex(paper)


async def extract_key_findings(paper: ParsedPaper) -> list[str]:
    """Extract key findings/contributions from a paper.

    Args:
        paper: Parsed paper

    Returns:
        List of key findings
    """
    prompt = f"""Extract 3-5 key findings or contributions from this paper.

Title: {paper.title}

Abstract: {paper.abstract}

Text excerpt:
{paper.full_text[:2000] if paper.full_text else ""}

List the key findings as a JSON array of strings:"""

    try:
        result = await get_llm_client().generate_json(
            prompt,
            system=SYSTEM_PROMPT,
        )
        if isinstance(result, list):
            return result
        return result.get("findings", result.get("key_findings", []))
    except Exception as e:
        logger.warning("key_findings_extraction_failed", error=str(e))
        return []


async def extract_methods_used(paper: ParsedPaper) -> list[str]:
    """Extract methods/techniques used in a paper.

    Args:
        paper: Parsed paper

    Returns:
        List of method names
    """
    prompt = f"""What methods, techniques, or approaches are used in this paper?

Title: {paper.title}

Abstract: {paper.abstract}

List the methods as a JSON array of strings (just names, no descriptions):"""

    try:
        result = await get_llm_client().generate_json(prompt, system=SYSTEM_PROMPT)
        if isinstance(result, list):
            return result
        return result.get("methods", [])
    except Exception as e:
        logger.warning("methods_extraction_failed", error=str(e))
        return []
