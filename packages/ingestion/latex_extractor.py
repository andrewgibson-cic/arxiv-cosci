"""LaTeX and mathematical entity extraction from papers.

Extracts and identifies:
- Equations (inline and display)
- Named equations (e.g., "Schrödinger equation")
- Theorems and proofs
- Conjectures and lemmas
- Mathematical constants
"""

import re
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()

# Equation patterns
DISPLAY_EQUATION_PATTERNS = [
    re.compile(r"\$\$(.+?)\$\$", re.DOTALL),  # $$...$$
    re.compile(r"\\\[(.+?)\\\]", re.DOTALL),  # \[...\]
    re.compile(r"\\begin\{equation\}(.+?)\\end\{equation\}", re.DOTALL),
    re.compile(r"\\begin\{equation\*\}(.+?)\\end\{equation\*\}", re.DOTALL),
    re.compile(r"\\begin\{align\}(.+?)\\end\{align\}", re.DOTALL),
    re.compile(r"\\begin\{align\*\}(.+?)\\end\{align\*\}", re.DOTALL),
    re.compile(r"\\begin\{eqnarray\}(.+?)\\end\{eqnarray\}", re.DOTALL),
    re.compile(r"\\begin\{gather\}(.+?)\\end\{gather\}", re.DOTALL),
]

INLINE_EQUATION_PATTERN = re.compile(r"\$([^$]+?)\$")

# Named equation patterns (physics/math specific)
NAMED_EQUATIONS = {
    r"Schr[öo]dinger\s+equation": "Schrödinger equation",
    r"Heisenberg\s+uncertainty": "Heisenberg uncertainty principle",
    r"Einstein\s+field\s+equation": "Einstein field equations",
    r"Maxwell'?s?\s+equations?": "Maxwell's equations",
    r"Dirac\s+equation": "Dirac equation",
    r"Klein-Gordon\s+equation": "Klein-Gordon equation",
    r"Navier-Stokes\s+equation": "Navier-Stokes equations",
    r"Euler'?s?\s+equation": "Euler's equation",
    r"Fourier\s+transform": "Fourier transform",
    r"Laplace\s+equation": "Laplace equation",
    r"Poisson\s+equation": "Poisson equation",
    r"Wave\s+equation": "Wave equation",
    r"Heat\s+equation": "Heat equation",
    r"Boltzmann\s+equation": "Boltzmann equation",
    r"Fermi-Dirac\s+distribution": "Fermi-Dirac distribution",
    r"Bose-Einstein\s+distribution": "Bose-Einstein distribution",
}

# Theorem patterns
THEOREM_PATTERNS = [
    re.compile(r"\\begin\{theorem\}(.+?)\\end\{theorem\}", re.DOTALL | re.IGNORECASE),
    re.compile(r"\\begin\{lemma\}(.+?)\\end\{lemma\}", re.DOTALL | re.IGNORECASE),
    re.compile(r"\\begin\{proposition\}(.+?)\\end\{proposition\}", re.DOTALL | re.IGNORECASE),
    re.compile(r"\\begin\{corollary\}(.+?)\\end\{corollary\}", re.DOTALL | re.IGNORECASE),
    re.compile(r"Theorem\s+(\d+(?:\.\d+)?)[:.]\s*(.+?)(?=\\n\\n|\Z)", re.DOTALL),
    re.compile(r"Lemma\s+(\d+(?:\.\d+)?)[:.]\s*(.+?)(?=\\n\\n|\Z)", re.DOTALL),
]

# Conjecture patterns
CONJECTURE_PATTERNS = [
    re.compile(r"\\begin\{conjecture\}(.+?)\\end\{conjecture\}", re.DOTALL | re.IGNORECASE),
    re.compile(r"Conjecture\s+(\d+(?:\.\d+)?)[:.]\s*(.+?)(?=\\n\\n|\Z)", re.DOTALL),
]

# Physical constants (common in physics papers)
PHYSICAL_CONSTANTS = {
    r"\\hbar": "reduced Planck constant",
    r"\\pi": "pi",
    r"speed\s+of\s+light": "speed of light (c)",
    r"Planck'?s?\s+constant": "Planck constant",
    r"gravitational\s+constant": "gravitational constant (G)",
    r"Boltzmann\s+constant": "Boltzmann constant",
    r"fine[\s-]structure\s+constant": "fine-structure constant",
}


@dataclass
class MathEntity:
    """A mathematical entity extracted from text."""

    type: str  # "equation", "theorem", "conjecture", "lemma", "constant"
    content: str  # LaTeX source or statement
    name: str | None = None  # Named entity (e.g., "Heisenberg uncertainty")
    context: str = ""  # Surrounding text
    section: str = ""  # Section where it appears
    number: str | None = None  # Equation/theorem number if present
    metadata: dict[str, Any] | None = None


class LaTeXExtractor:
    """Extractor for LaTeX equations and mathematical entities."""

    def __init__(self) -> None:
        """Initialize LaTeX extractor."""
        pass

    def extract_display_equations(self, text: str) -> list[MathEntity]:
        """Extract display (block) equations.

        Args:
            text: Document text

        Returns:
            List of equation entities
        """
        equations: list[MathEntity] = []
        seen: set[str] = set()

        for pattern in DISPLAY_EQUATION_PATTERNS:
            for match in pattern.finditer(text):
                content = match.group(1).strip()

                # Skip if empty or already seen
                if not content or content in seen:
                    continue

                seen.add(content)

                # Extract context (100 chars before and after)
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end].replace("\n", " ").strip()

                # Check for equation number
                number = self._extract_equation_number(context)

                equations.append(
                    MathEntity(
                        type="equation",
                        content=content,
                        context=context,
                        number=number,
                        metadata={"display": True},
                    )
                )

        logger.debug("extracted_display_equations", count=len(equations))
        return equations

    def extract_inline_equations(self, text: str, min_length: int = 4) -> list[MathEntity]:
        """Extract inline equations.

        Args:
            text: Document text
            min_length: Minimum equation length to avoid false positives

        Returns:
            List of equation entities
        """
        equations: list[MathEntity] = []
        seen: set[str] = set()

        for match in INLINE_EQUATION_PATTERN.finditer(text):
            content = match.group(1).strip()

            # Skip short or numeric-only matches
            if len(content) < min_length or content.isdigit():
                continue

            if content in seen:
                continue

            seen.add(content)

            # Extract context
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end].replace("\n", " ").strip()

            equations.append(
                MathEntity(
                    type="equation",
                    content=content,
                    context=context,
                    metadata={"display": False},
                )
            )

        logger.debug("extracted_inline_equations", count=len(equations))
        return equations

    def extract_named_equations(self, text: str) -> list[MathEntity]:
        """Extract named equations (e.g., "Schrödinger equation").

        Args:
            text: Document text

        Returns:
            List of named equation entities
        """
        entities: list[MathEntity] = []

        for pattern, name in NAMED_EQUATIONS.items():
            regex = re.compile(pattern, re.IGNORECASE)
            for match in regex.finditer(text):
                # Extract context
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 200)
                context = text[start:end].replace("\n", " ").strip()

                entities.append(
                    MathEntity(
                        type="equation",
                        content=match.group(0),
                        name=name,
                        context=context,
                        metadata={"named": True},
                    )
                )

        logger.debug("extracted_named_equations", count=len(entities))
        return entities

    def extract_theorems(self, text: str) -> list[MathEntity]:
        """Extract theorems, lemmas, and propositions.

        Args:
            text: Document text

        Returns:
            List of theorem entities
        """
        theorems: list[MathEntity] = []

        for pattern in THEOREM_PATTERNS:
            for match in pattern.finditer(text):
                if len(match.groups()) == 1:
                    # Environment format
                    content = match.group(1).strip()
                    number = None
                else:
                    # Numbered format
                    number = match.group(1)
                    content = match.group(2).strip()

                # Extract context
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end].replace("\n", " ").strip()

                # Determine type from match
                match_text = match.group(0).lower()
                if "lemma" in match_text:
                    entity_type = "lemma"
                elif "proposition" in match_text:
                    entity_type = "proposition"
                elif "corollary" in match_text:
                    entity_type = "corollary"
                else:
                    entity_type = "theorem"

                theorems.append(
                    MathEntity(
                        type=entity_type,
                        content=content,
                        context=context,
                        number=number,
                    )
                )

        logger.debug("extracted_theorems", count=len(theorems))
        return theorems

    def extract_conjectures(self, text: str) -> list[MathEntity]:
        """Extract conjectures.

        Args:
            text: Document text

        Returns:
            List of conjecture entities
        """
        conjectures: list[MathEntity] = []

        for pattern in CONJECTURE_PATTERNS:
            for match in pattern.finditer(text):
                if len(match.groups()) == 1:
                    content = match.group(1).strip()
                    number = None
                else:
                    number = match.group(1)
                    content = match.group(2).strip()

                # Extract context
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end].replace("\n", " ").strip()

                conjectures.append(
                    MathEntity(
                        type="conjecture",
                        content=content,
                        context=context,
                        number=number,
                    )
                )

        logger.debug("extracted_conjectures", count=len(conjectures))
        return conjectures

    def extract_physical_constants(self, text: str) -> list[MathEntity]:
        """Extract references to physical constants.

        Args:
            text: Document text

        Returns:
            List of constant entities
        """
        constants: list[MathEntity] = []

        for pattern, name in PHYSICAL_CONSTANTS.items():
            regex = re.compile(pattern, re.IGNORECASE)
            for match in regex.finditer(text):
                # Extract context
                start = max(0, match.start() - 150)
                end = min(len(text), match.end() + 150)
                context = text[start:end].replace("\n", " ").strip()

                constants.append(
                    MathEntity(
                        type="constant",
                        content=match.group(0),
                        name=name,
                        context=context,
                    )
                )

        logger.debug("extracted_constants", count=len(constants))
        return constants

    def extract_all(self, text: str, section: str = "") -> dict[str, list[MathEntity]]:
        """Extract all mathematical entities from text.

        Args:
            text: Document text
            section: Optional section name for context

        Returns:
            Dictionary mapping entity types to lists of entities
        """
        entities: dict[str, list[MathEntity]] = {
            "display_equations": self.extract_display_equations(text),
            "inline_equations": self.extract_inline_equations(text),
            "named_equations": self.extract_named_equations(text),
            "theorems": self.extract_theorems(text),
            "conjectures": self.extract_conjectures(text),
            "constants": self.extract_physical_constants(text),
        }

        # Add section context to all entities
        if section:
            for entity_list in entities.values():
                for entity in entity_list:
                    entity.section = section

        total = sum(len(v) for v in entities.values())
        logger.info("extracted_all_math_entities", total=total, by_type=
                    {k: len(v) for k, v in entities.items()})

        return entities

    def _extract_equation_number(self, context: str) -> str | None:
        """Extract equation number from context if present.

        Args:
            context: Text surrounding equation

        Returns:
            Equation number or None
        """
        # Look for patterns like (1), (2.1), etc.
        number_pattern = re.compile(r"\((\d+(?:\.\d+)?)\)")
        match = number_pattern.search(context)
        if match:
            return match.group(1)
        return None