"""
Hypothesis Generation using LLM and Structural Holes

This module uses Gemini/LLM to generate research hypotheses based on
detected structural holes in the knowledge graph.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from packages.ai.llm_base import LLMClient
from packages.ml.structural_holes import StructuralHole

logger = logging.getLogger(__name__)


@dataclass
class ResearchHypothesis:
    """
    A generated research hypothesis connecting structural holes.
    """
    
    hole: StructuralHole
    hypothesis: str
    rationale: str
    confidence: float  # 0-1
    research_questions: List[str]
    potential_impact: str
    suggested_methods: List[str]


class HypothesisGenerator:
    """
    Generate research hypotheses from structural holes using LLM.
    
    Features:
    - Contextual hypothesis generation
    - Multi-shot prompting for quality
    - Confidence scoring
    - Research question generation
    """
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize hypothesis generator.
        
        Args:
            llm_client: LLM client (Gemini, Groq, or Ollama)
        """
        self.llm = llm_client
    
    async def generate_hypothesis(
        self,
        hole: StructuralHole,
        context: Optional[str] = None,
    ) -> ResearchHypothesis:
        """
        Generate a research hypothesis for a structural hole.
        
        Args:
            hole: Structural hole to generate hypothesis for
            context: Additional context about the domain
            
        Returns:
            Research hypothesis with supporting details
        """
        # Build prompt based on hole type
        prompt = self._build_hypothesis_prompt(hole, context)
        
        # Generate hypothesis using LLM
        response = await self.llm.generate(
            prompt,
            temperature=0.7,  # Some creativity
            max_tokens=1000,
        )
        
        # Parse response into structured hypothesis
        hypothesis = self._parse_hypothesis_response(response, hole)
        
        logger.info(
            f"Generated hypothesis for {hole.source_type} → {hole.target_type} gap: "
            f"{hypothesis.hypothesis[:100]}..."
        )
        
        return hypothesis
    
    def _build_hypothesis_prompt(
        self,
        hole: StructuralHole,
        context: Optional[str] = None,
    ) -> str:
        """
        Build a prompt for hypothesis generation.
        
        Args:
            hole: Structural hole
            context: Additional context
            
        Returns:
            Formatted prompt string
        """
        if hole.source_type == "Paper" and hole.target_type == "Paper":
            return self._build_paper_paper_prompt(hole, context)
        elif hole.source_type == "Concept" and hole.target_type == "Concept":
            return self._build_concept_concept_prompt(hole, context)
        else:
            return self._build_generic_prompt(hole, context)
    
    def _build_paper_paper_prompt(
        self,
        hole: StructuralHole,
        context: Optional[str] = None,
    ) -> str:
        """Build prompt for paper-to-paper gaps."""
        shared = ", ".join(hole.shared_neighbors[:3])
        
        prompt = f"""You are a scientific research advisor analyzing citation networks.

**Structural Gap Identified:**
- Source Paper: "{hole.source_name}"
- Target Paper: "{hole.target_name}"
- Gap Type: {hole.reason}
- Shared Citations: {shared}

**Task:**
Generate a research hypothesis explaining why these papers should be connected but aren't.

**Your response should include:**
1. **Hypothesis**: A clear, testable hypothesis (2-3 sentences)
2. **Rationale**: Why this connection matters (2-3 sentences)
3. **Research Questions**: 3 specific research questions this hypothesis raises
4. **Potential Impact**: Expected impact on the field (1-2 sentences)
5. **Suggested Methods**: 3 methods or approaches to test this hypothesis

**Format your response as:**
HYPOTHESIS: [your hypothesis]
RATIONALE: [your rationale]
QUESTIONS:
- [question 1]
- [question 2]
- [question 3]
IMPACT: [potential impact]
METHODS:
- [method 1]
- [method 2]
- [method 3]
"""
        
        if context:
            prompt += f"\n**Additional Context:**\n{context}\n"
        
        return prompt
    
    def _build_concept_concept_prompt(
        self,
        hole: StructuralHole,
        context: Optional[str] = None,
    ) -> str:
        """Build prompt for concept-to-concept gaps."""
        shared = ", ".join(hole.shared_neighbors[:3])
        
        prompt = f"""You are a scientific research advisor analyzing knowledge graphs.

**Conceptual Gap Identified:**
- Concept A: "{hole.source_name}" ({hole.metadata.get('source_concept_type', 'unknown')})
- Concept B: "{hole.target_name}" ({hole.metadata.get('target_concept_type', 'unknown')})
- Gap Type: {hole.reason}
- Related Papers: {shared}

**Task:**
Generate a research hypothesis about the relationship between these concepts.

**Your response should include:**
1. **Hypothesis**: A clear hypothesis about how these concepts relate (2-3 sentences)
2. **Rationale**: Why this relationship is scientifically interesting (2-3 sentences)
3. **Research Questions**: 3 specific questions this hypothesis raises
4. **Potential Impact**: How discovering this relationship could advance the field
5. **Suggested Methods**: 3 methods to investigate this relationship

**Format your response as:**
HYPOTHESIS: [your hypothesis]
RATIONALE: [your rationale]
QUESTIONS:
- [question 1]
- [question 2]
- [question 3]
IMPACT: [potential impact]
METHODS:
- [method 1]
- [method 2]
- [method 3]
"""
        
        if context:
            prompt += f"\n**Additional Context:**\n{context}\n"
        
        return prompt
    
    def _build_generic_prompt(
        self,
        hole: StructuralHole,
        context: Optional[str] = None,
    ) -> str:
        """Build generic prompt for other gap types."""
        prompt = f"""You are a scientific research advisor analyzing knowledge gaps.

**Gap Identified:**
- Source: "{hole.source_name}" (Type: {hole.source_type})
- Target: "{hole.target_name}" (Type: {hole.target_type})
- Relationship: {hole.reason}
- Score: {hole.score:.2f}

**Task:**
Generate a research hypothesis about this gap in the knowledge graph.

Provide:
1. HYPOTHESIS: A testable hypothesis (2-3 sentences)
2. RATIONALE: Why this matters (2-3 sentences)
3. QUESTIONS: 3 research questions
4. IMPACT: Potential impact (1-2 sentences)
5. METHODS: 3 suggested methods

Format as shown above.
"""
        
        if context:
            prompt += f"\n**Context:** {context}\n"
        
        return prompt
    
    def _parse_hypothesis_response(
        self,
        response: str,
        hole: StructuralHole,
    ) -> ResearchHypothesis:
        """
        Parse LLM response into structured hypothesis.
        
        Args:
            response: Raw LLM response
            hole: Original structural hole
            
        Returns:
            Structured research hypothesis
        """
        lines = response.strip().split("\n")
        
        hypothesis = ""
        rationale = ""
        questions = []
        impact = ""
        methods = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("HYPOTHESIS:"):
                current_section = "hypothesis"
                hypothesis = line.replace("HYPOTHESIS:", "").strip()
            elif line.startswith("RATIONALE:"):
                current_section = "rationale"
                rationale = line.replace("RATIONALE:", "").strip()
            elif line.startswith("QUESTIONS:"):
                current_section = "questions"
            elif line.startswith("IMPACT:"):
                current_section = "impact"
                impact = line.replace("IMPACT:", "").strip()
            elif line.startswith("METHODS:"):
                current_section = "methods"
            elif line.startswith("-") or line.startswith("•"):
                # List item
                item = line.lstrip("-•").strip()
                if current_section == "questions":
                    questions.append(item)
                elif current_section == "methods":
                    methods.append(item)
            elif line and current_section:
                # Continuation of current section
                if current_section == "hypothesis":
                    hypothesis += " " + line
                elif current_section == "rationale":
                    rationale += " " + line
                elif current_section == "impact":
                    impact += " " + line
        
        # Calculate confidence based on response quality
        confidence = self._calculate_confidence(
            hypothesis, rationale, questions, methods
        )
        
        return ResearchHypothesis(
            hole=hole,
            hypothesis=hypothesis or "No hypothesis generated",
            rationale=rationale or "No rationale provided",
            confidence=confidence,
            research_questions=questions or ["No questions generated"],
            potential_impact=impact or "Impact unknown",
            suggested_methods=methods or ["No methods suggested"],
        )
    
    def _calculate_confidence(
        self,
        hypothesis: str,
        rationale: str,
        questions: List[str],
        methods: List[str],
    ) -> float:
        """
        Calculate confidence score for generated hypothesis.
        
        Args:
            hypothesis: Generated hypothesis text
            rationale: Rationale text
            questions: List of research questions
            methods: List of suggested methods
            
        Returns:
            Confidence score (0-1)
        """
        score = 0.0
        
        # Check completeness
        if hypothesis and len(hypothesis) > 20:
            score += 0.3
        if rationale and len(rationale) > 20:
            score += 0.2
        if len(questions) >= 3:
            score += 0.2
        if len(methods) >= 3:
            score += 0.2
        
        # Check quality indicators
        if any(word in hypothesis.lower() for word in ["because", "therefore", "suggests", "implies"]):
            score += 0.05
        if any(word in rationale.lower() for word in ["novel", "important", "significant", "advance"]):
            score += 0.05
        
        return min(1.0, score)
    
    async def generate_batch(
        self,
        holes: List[StructuralHole],
        max_hypotheses: int = 10,
        context: Optional[str] = None,
    ) -> List[ResearchHypothesis]:
        """
        Generate hypotheses for multiple structural holes.
        
        Args:
            holes: List of structural holes
            max_hypotheses: Maximum number of hypotheses to generate
            context: Additional context
            
        Returns:
            List of research hypotheses
        """
        # Sort by score and take top N
        sorted_holes = sorted(holes, key=lambda h: h.score, reverse=True)
        top_holes = sorted_holes[:max_hypotheses]
        
        hypotheses = []
        
        for i, hole in enumerate(top_holes, 1):
            logger.info(f"Generating hypothesis {i}/{len(top_holes)}...")
            
            try:
                hypothesis = await self.generate_hypothesis(hole, context)
                hypotheses.append(hypothesis)
            except Exception as e:
                logger.error(f"Failed to generate hypothesis for hole: {e}")
                continue
        
        logger.info(f"Generated {len(hypotheses)} hypotheses")
        
        # Sort by confidence
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        
        return hypotheses
    
    def to_markdown(self, hypothesis: ResearchHypothesis) -> str:
        """
        Convert hypothesis to markdown format.
        
        Args:
            hypothesis: Research hypothesis
            
        Returns:
            Formatted markdown string
        """
        md = f"""## Research Hypothesis

**Source:** {hypothesis.hole.source_name}  
**Target:** {hypothesis.hole.target_name}  
**Gap Type:** {hypothesis.hole.reason}  
**Confidence:** {hypothesis.confidence:.2%}

### Hypothesis
{hypothesis.hypothesis}

### Rationale
{hypothesis.rationale}

### Research Questions
"""
        
        for i, question in enumerate(hypothesis.research_questions, 1):
            md += f"{i}. {question}\n"
        
        md += f"\n### Potential Impact\n{hypothesis.potential_impact}\n"
        
        md += "\n### Suggested Methods\n"
        for method in hypothesis.suggested_methods:
            md += f"- {method}\n"
        
        return md