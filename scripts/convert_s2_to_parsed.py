#!/usr/bin/env python3
"""Convert Semantic Scholar metadata to ParsedPaper format for testing."""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.ingestion.models import ParsedPaper, ParserType


def convert_s2_metadata(s2_paper: dict) -> ParsedPaper:
    """Convert S2 metadata to ParsedPaper."""
    return ParsedPaper(
        arxiv_id=s2_paper["id"],
        title=s2_paper["title"],
        authors=s2_paper["authors"].split(", ") if s2_paper["authors"] else [],
        abstract=s2_paper["abstract"] or "",
        categories=[cat.strip() for cat in s2_paper.get("categories", "").split(",") if cat.strip()],
        published_date=datetime.now(),  # Approximate from update_date
        full_text="",  # No full text from S2 API (metadata only)
        sections=[],
        citations=[],
        equations=[],
        parser_used=ParserType.PYMUPDF,  # Default parser type
        parse_confidence=0.5,  # Lower confidence since it's just metadata
    )


def main():
    """Convert S2 papers to ParsedPaper format."""
    input_file = Path("data/sample_papers.json")
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load S2 papers
    papers = json.loads(input_file.read_text())
    print(f"Converting {len(papers)} papers...")
    
    # Convert and save each paper
    for paper_data in papers:
        try:
            parsed = convert_s2_metadata(paper_data)
            output_file = output_dir / f"{parsed.arxiv_id.replace('/', '_')}.json"
            output_file.write_text(parsed.model_dump_json(indent=2))
            print(f"✓ Converted {parsed.arxiv_id}: {parsed.title[:60]}...")
        except Exception as e:
            print(f"✗ Failed to convert {paper_data.get('id', 'unknown')}: {e}")
    
    print(f"\nSaved {len(papers)} papers to {output_dir}")


if __name__ == "__main__":
    main()