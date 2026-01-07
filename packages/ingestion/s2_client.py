"""Semantic Scholar API client for fetching paper metadata and citations.

This module provides async access to Semantic Scholar's rich dataset including:
- Paper metadata (title, authors, abstract, venue)
- Citation data (incoming/outgoing with context)
- Influence metrics (citation counts, influential citations)
- Related papers and recommendations
- Author profiles and affiliations

API Docs: https://api.semanticscholar.org/api-docs/
"""

import asyncio
from typing import Any

import aiohttp
from semanticscholar import SemanticScholar
from semanticscholar.Paper import Paper
from tenacity import retry, stop_after_attempt, wait_exponential

from packages.ingestion.models import Citation, CitationIntent, PaperMetadata


class S2Client:
    """Async wrapper for Semantic Scholar API with rate limiting and retries."""

    def __init__(self, api_key: str | None = None, timeout: int = 30):
        """Initialize S2 client.

        Args:
            api_key: Optional S2 API key for higher rate limits (10 req/sec vs 1 req/sec)
            timeout: Request timeout in seconds
        """
        self.client = SemanticScholar(api_key=api_key, timeout=timeout)
        self.api_key = api_key
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "S2Client":
        """Context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Context manager exit."""
        if self.session:
            await self.session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_paper_by_arxiv_id(self, arxiv_id: str) -> Paper | None:
        """Fetch paper metadata from Semantic Scholar by arXiv ID.

        Args:
            arxiv_id: ArXiv identifier (e.g., '2401.12345')

        Returns:
            Paper object or None if not found

        Rate Limits:
            - Without API key: 1 request/sec
            - With API key: 10 requests/sec
        """
        try:
            # Run sync S2 client in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            paper = await loop.run_in_executor(
                None,
                self.client.get_paper,
                f"ARXIV:{arxiv_id}",
            )
            return paper
        except Exception as e:
            print(f"Failed to fetch paper {arxiv_id}: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_paper_citations(
        self, arxiv_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch incoming citations for a paper.

        Args:
            arxiv_id: ArXiv identifier
            limit: Maximum citations to fetch

        Returns:
            List of citation dicts with context and citing paper metadata
        """
        try:
            loop = asyncio.get_event_loop()
            paper = await loop.run_in_executor(
                None,
                self.client.get_paper,
                f"ARXIV:{arxiv_id}",
            )
            if not paper or not paper.citations:
                return []

            citations = []
            for cite in paper.citations[:limit]:
                citations.append(
                    {
                        "citing_paper_id": cite.paperId,
                        "title": cite.title,
                        "year": cite.year,
                        "authors": [a.name for a in cite.authors] if cite.authors else [],
                        "citation_count": cite.citationCount or 0,
                    }
                )
            return citations

        except Exception as e:
            print(f"Failed to fetch citations for {arxiv_id}: {e}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_paper_references(
        self, arxiv_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch outgoing references from a paper.

        Args:
            arxiv_id: ArXiv identifier
            limit: Maximum references to fetch

        Returns:
            List of reference dicts with metadata
        """
        try:
            loop = asyncio.get_event_loop()
            paper = await loop.run_in_executor(
                None,
                self.client.get_paper,
                f"ARXIV:{arxiv_id}",
            )
            if not paper or not paper.references:
                return []

            references = []
            for ref in paper.references[:limit]:
                references.append(
                    {
                        "paper_id": ref.paperId,
                        "title": ref.title,
                        "year": ref.year,
                        "authors": [a.name for a in ref.authors] if ref.authors else [],
                        "arxiv_id": self._extract_arxiv_id(ref.externalIds or {}),
                        "doi": ref.externalIds.get("DOI") if ref.externalIds else None,
                    }
                )
            return references

        except Exception as e:
            print(f"Failed to fetch references for {arxiv_id}: {e}")
            return []

    async def search_papers(
        self, query: str, limit: int = 10, fields: list[str] | None = None
    ) -> list[Paper]:
        """Semantic search for papers by query string.

        Args:
            query: Search query (natural language)
            limit: Maximum results to return
            fields: Optional list of fields to retrieve

        Returns:
            List of Paper objects matching the query
        """
        if fields is None:
            fields = [
                "title",
                "abstract",
                "year",
                "authors",
                "citationCount",
                "externalIds",
            ]

        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.client.search_paper(query, limit=limit, fields=fields),
            )
            return results if results else []

        except Exception as e:
            print(f"Search failed for query '{query}': {e}")
            return []

    def paper_to_metadata(self, paper: Paper) -> PaperMetadata:
        """Convert Semantic Scholar Paper to our PaperMetadata model.

        Args:
            paper: S2 Paper object

        Returns:
            PaperMetadata instance
        """
        arxiv_id = self._extract_arxiv_id(paper.externalIds or {})
        if not arxiv_id:
            arxiv_id = paper.paperId  # Fallback to S2 ID

        authors_str = ", ".join([a.name for a in paper.authors]) if paper.authors else ""

        return PaperMetadata(
            id=arxiv_id,
            title=paper.title or "",
            abstract=paper.abstract or "",
            authors=authors_str,
            categories="",  # S2 doesn't have arXiv categories directly
            update_date=str(paper.year) if paper.year else "",
            doi=paper.externalIds.get("DOI") if paper.externalIds else None,
            authors_parsed=[],
            submitter=None,
            comments=paper.tldr.text if paper.tldr else None,
            journal_ref=paper.venue if paper.venue else None,
            report_no=None,
            license=None,
            versions=[],
        )

    def _extract_arxiv_id(self, external_ids: dict[str, Any]) -> str | None:
        """Extract arXiv ID from external IDs dict.

        Args:
            external_ids: Dict like {'ArXiv': '2401.12345', 'DOI': '...'}

        Returns:
            ArXiv ID string or None
        """
        arxiv_id = external_ids.get("ArXiv")
        if arxiv_id:
            # Remove 'arXiv:' prefix if present
            return arxiv_id.replace("arXiv:", "")
        return None

    async def get_recommendations(self, arxiv_id: str, limit: int = 10) -> list[Paper]:
        """Get recommended papers based on a seed paper.

        Args:
            arxiv_id: ArXiv identifier
            limit: Maximum recommendations

        Returns:
            List of recommended Paper objects
        """
        try:
            loop = asyncio.get_event_loop()
            paper = await loop.run_in_executor(
                None,
                self.client.get_paper,
                f"ARXIV:{arxiv_id}",
            )
            if not paper:
                return []

            # Get recommendations via similar papers
            recommendations = await loop.run_in_executor(
                None,
                lambda: self.client.get_recommended_papers(paper.paperId, limit=limit),
            )
            return recommendations if recommendations else []

        except Exception as e:
            print(f"Failed to get recommendations for {arxiv_id}: {e}")
            return []

    async def batch_fetch_papers(
        self, arxiv_ids: list[str], delay: float = 0.1
    ) -> list[Paper]:
        """Fetch multiple papers with rate limiting.

        Args:
            arxiv_ids: List of arXiv IDs
            delay: Delay between requests in seconds (0.1s = 10 req/sec)

        Returns:
            List of successfully fetched Papers
        """
        papers = []
        for arxiv_id in arxiv_ids:
            paper = await self.get_paper_by_arxiv_id(arxiv_id)
            if paper:
                papers.append(paper)
            await asyncio.sleep(delay)  # Rate limiting
        return papers
