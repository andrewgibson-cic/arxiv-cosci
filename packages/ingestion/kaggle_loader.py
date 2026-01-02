"""Load and filter arXiv metadata from Kaggle dataset.

The Kaggle arXiv dataset contains metadata for all arXiv papers in JSON Lines format.
This module provides utilities to:
- Load the dataset efficiently (streaming for large files)
- Filter papers by category (physics/math focus)
- Create subsets for initial development
"""

import json
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import TextIO

import structlog

from packages.ingestion.models import ArxivCategory, PaperMetadata

logger = structlog.get_logger()

# Physics and math category prefixes to include
PHYSICS_MATH_PREFIXES = (
    "hep-",  # High-energy physics
    "gr-qc",  # General relativity
    "quant-ph",  # Quantum physics
    "cond-mat",  # Condensed matter
    "astro-ph",  # Astrophysics
    "nucl-",  # Nuclear physics
    "math.",  # Mathematics
    "math-ph",  # Mathematical physics
    "nlin.",  # Nonlinear sciences
    "physics.",  # General physics
)


def is_physics_math_paper(categories: str) -> bool:
    """Check if paper belongs to physics or math categories.

    Args:
        categories: Space-separated category string

    Returns:
        True if any category matches physics/math prefixes
    """
    for category in categories.split():
        for prefix in PHYSICS_MATH_PREFIXES:
            if category.startswith(prefix):
                return True
    return False


def stream_kaggle_metadata(
    file_path: Path,
    *,
    filter_physics_math: bool = True,
    limit: int | None = None,
) -> Generator[PaperMetadata, None, None]:
    """Stream paper metadata from Kaggle JSON Lines file.

    Efficiently processes large files without loading everything into memory.

    Args:
        file_path: Path to arxiv-metadata-oai-snapshot.json
        filter_physics_math: If True, only yield physics/math papers
        limit: Maximum number of papers to yield (None for all)

    Yields:
        PaperMetadata objects for matching papers
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Kaggle dataset not found: {file_path}")

    count = 0
    filtered_count = 0

    logger.info("streaming_kaggle_metadata", path=str(file_path), filter=filter_physics_math)

    with open(file_path, encoding="utf-8") as f:
        for line in f:
            if limit and count >= limit:
                break

            try:
                data = json.loads(line)
                categories = data.get("categories", "")

                if filter_physics_math and not is_physics_math_paper(categories):
                    filtered_count += 1
                    continue

                metadata = PaperMetadata.model_validate(data)
                yield metadata
                count += 1

                if count % 10000 == 0:
                    logger.debug("progress", loaded=count, filtered=filtered_count)

            except json.JSONDecodeError as e:
                logger.warning("json_decode_error", error=str(e))
            except Exception as e:
                logger.warning("metadata_parse_error", error=str(e), data=data.get("id"))

    logger.info(
        "streaming_complete",
        total_loaded=count,
        total_filtered=filtered_count,
    )


def load_kaggle_metadata(
    file_path: Path,
    *,
    filter_physics_math: bool = True,
    limit: int | None = None,
) -> list[PaperMetadata]:
    """Load all matching paper metadata into memory.

    For smaller subsets or when random access is needed.

    Args:
        file_path: Path to arxiv-metadata-oai-snapshot.json
        filter_physics_math: If True, only load physics/math papers
        limit: Maximum number of papers to load

    Returns:
        List of PaperMetadata objects
    """
    return list(
        stream_kaggle_metadata(
            file_path,
            filter_physics_math=filter_physics_math,
            limit=limit,
        )
    )


def filter_by_categories(
    papers: Iterator[PaperMetadata],
    categories: list[str | ArxivCategory],
) -> Generator[PaperMetadata, None, None]:
    """Filter papers by specific categories.

    Args:
        papers: Iterator of PaperMetadata
        categories: List of category strings or ArxivCategory enums

    Yields:
        Papers matching any of the specified categories
    """
    category_set = {
        c.value if isinstance(c, ArxivCategory) else c
        for c in categories
    }

    for paper in papers:
        paper_categories = set(paper.category_list)
        if paper_categories & category_set:
            yield paper


def get_category_counts(file_path: Path, limit: int | None = None) -> dict[str, int]:
    """Count papers per category in the dataset.

    Useful for understanding dataset composition.

    Args:
        file_path: Path to Kaggle dataset
        limit: Maximum papers to scan

    Returns:
        Dictionary mapping category to paper count
    """
    counts: dict[str, int] = {}

    for paper in stream_kaggle_metadata(file_path, filter_physics_math=False, limit=limit):
        for category in paper.category_list:
            counts[category] = counts.get(category, 0) + 1

    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


def create_subset(
    input_path: Path,
    output_path: Path,
    *,
    categories: list[str] | None = None,
    limit: int | None = None,
) -> int:
    """Create a filtered subset of the Kaggle dataset.

    Args:
        input_path: Path to full Kaggle dataset
        output_path: Path for filtered output (JSON Lines)
        categories: Specific categories to include (None for all physics/math)
        limit: Maximum papers in subset

    Returns:
        Number of papers written
    """
    count = 0

    papers = stream_kaggle_metadata(input_path, filter_physics_math=True, limit=None)

    if categories:
        papers = filter_by_categories(papers, categories)

    with open(output_path, "w", encoding="utf-8") as f:
        for paper in papers:
            if limit and count >= limit:
                break

            f.write(paper.model_dump_json() + "\n")
            count += 1

    logger.info("subset_created", path=str(output_path), count=count)
    return count
