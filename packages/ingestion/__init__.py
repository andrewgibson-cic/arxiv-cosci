"""Data ingestion package for ArXiv papers.

This package handles:
- Loading metadata from Kaggle arXiv dataset
- Downloading PDFs with rate limiting
- Text extraction from PDFs
"""

from packages.ingestion.models import ArxivPaper, PaperMetadata, ParsedPaper

__all__ = ["ArxivPaper", "PaperMetadata", "ParsedPaper"]
