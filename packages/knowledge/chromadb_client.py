"""ChromaDB vector storage for semantic search.

Provides embedding storage and similarity search for papers:
- Paper embeddings (title + abstract)
- Concept embeddings
- Hybrid search combining vector similarity with graph filters
"""

import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
import structlog

from packages.ingestion.models import ParsedPaper

logger = structlog.get_logger()

# Default embedding model for sentence-transformers
DEFAULT_EMBEDDING_MODEL = "all-mpnet-base-v2"

# ChromaDB collection names
PAPERS_COLLECTION = "papers"
CONCEPTS_COLLECTION = "concepts"


class ChromaDBClient:
    """ChromaDB client for vector storage and similarity search."""

    def __init__(
        self,
        persist_dir: Path | None = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        """Initialize ChromaDB client.

        Args:
            persist_dir: Directory for persistent storage (default: data/chroma)
            embedding_model: sentence-transformers model name
        """
        self.persist_dir = persist_dir or Path(
            os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
        )
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.embedding_model = embedding_model
        self._client: chromadb.PersistentClient | None = None
        self._embedding_fn: Any = None
        self._papers_collection: Any = None
        self._concepts_collection: Any = None

    def _get_client(self) -> chromadb.PersistentClient:
        """Get or create ChromaDB client."""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False),
            )
            logger.info("chromadb_initialized", path=str(self.persist_dir))
        return self._client

    def _get_embedding_fn(self) -> Any:
        """Get or create embedding function."""
        if self._embedding_fn is None:
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

            self._embedding_fn = SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model,
                device="mps",  # Apple Silicon GPU
            )
            logger.info("embedding_fn_initialized", model=self.embedding_model)
        return self._embedding_fn

    def _get_papers_collection(self) -> Any:
        """Get or create papers collection."""
        if self._papers_collection is None:
            client = self._get_client()
            self._papers_collection = client.get_or_create_collection(
                name=PAPERS_COLLECTION,
                embedding_function=self._get_embedding_fn(),
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("papers_collection_ready", name=PAPERS_COLLECTION)
        return self._papers_collection

    def _get_concepts_collection(self) -> Any:
        """Get or create concepts collection."""
        if self._concepts_collection is None:
            client = self._get_client()
            self._concepts_collection = client.get_or_create_collection(
                name=CONCEPTS_COLLECTION,
                embedding_function=self._get_embedding_fn(),
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("concepts_collection_ready", name=CONCEPTS_COLLECTION)
        return self._concepts_collection

    def add_paper(self, paper: ParsedPaper) -> None:
        """Add a paper to the vector store.

        Embeds title + abstract for semantic search.

        Args:
            paper: Parsed paper to add
        """
        collection = self._get_papers_collection()

        # Combine title and abstract for embedding
        text = f"{paper.title}\n\n{paper.abstract}"

        collection.upsert(
            ids=[paper.arxiv_id],
            documents=[text],
            metadatas=[
                {
                    "title": paper.title,
                    "primary_category": paper.categories[0] if paper.categories else "",
                    "author_count": len(paper.authors),
                    "equation_count": len(paper.equations),
                    "citation_count": len(paper.citations),
                }
            ],
        )
        logger.debug("paper_embedded", arxiv_id=paper.arxiv_id)

    def add_papers_batch(self, papers: list[ParsedPaper]) -> int:
        """Add multiple papers to the vector store.

        Args:
            papers: List of parsed papers

        Returns:
            Number of papers added
        """
        if not papers:
            return 0

        collection = self._get_papers_collection()

        ids = [p.arxiv_id for p in papers]
        documents = [f"{p.title}\n\n{p.abstract}" for p in papers]
        metadatas = [
            {
                "title": p.title,
                "primary_category": p.categories[0] if p.categories else "",
                "author_count": len(p.authors),
                "equation_count": len(p.equations),
                "citation_count": len(p.citations),
            }
            for p in papers
        ]

        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        logger.info("papers_batch_embedded", count=len(papers))
        return len(papers)

    def search_papers(
        self,
        query: str,
        n_results: int = 10,
        category_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar papers.

        Args:
            query: Natural language search query
            n_results: Maximum results to return
            category_filter: Optional category to filter by

        Returns:
            List of matching papers with similarity scores
        """
        collection = self._get_papers_collection()

        where = None
        if category_filter:
            where = {"primary_category": category_filter}

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        papers = []
        if results["ids"] and results["ids"][0]:
            for i, arxiv_id in enumerate(results["ids"][0]):
                paper = {
                    "arxiv_id": arxiv_id,
                    "distance": results["distances"][0][i] if results["distances"] else None,
                    "similarity": 1 - results["distances"][0][i] if results["distances"] else None,
                }
                if results["metadatas"] and results["metadatas"][0]:
                    paper.update(results["metadatas"][0][i])
                if results["documents"] and results["documents"][0]:
                    paper["document"] = results["documents"][0][i]
                papers.append(paper)

        logger.debug("search_complete", query=query[:50], results=len(papers))
        return papers

    def get_similar_papers(
        self,
        arxiv_id: str,
        n_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Find papers similar to a given paper.

        Args:
            arxiv_id: The reference paper's ID
            n_results: Maximum results to return

        Returns:
            List of similar papers with scores
        """
        collection = self._get_papers_collection()

        # Get the paper's embedding
        result = collection.get(ids=[arxiv_id], include=["embeddings"])

        if not result["embeddings"] or not result["embeddings"][0]:
            logger.warning("paper_not_found", arxiv_id=arxiv_id)
            return []

        embedding = result["embeddings"][0]

        # Query with the embedding
        results = collection.query(
            query_embeddings=[embedding],
            n_results=n_results + 1,  # Include self
            include=["metadatas", "distances"],
        )

        # Filter out the query paper itself
        papers = []
        if results["ids"] and results["ids"][0]:
            for i, result_id in enumerate(results["ids"][0]):
                if result_id != arxiv_id:
                    paper = {
                        "arxiv_id": result_id,
                        "distance": results["distances"][0][i] if results["distances"] else None,
                        "similarity": 1 - results["distances"][0][i] if results["distances"] else None,
                    }
                    if results["metadatas"] and results["metadatas"][0]:
                        paper.update(results["metadatas"][0][i])
                    papers.append(paper)

        return papers[:n_results]

    def get_stats(self) -> dict[str, int]:
        """Get collection statistics.

        Returns:
            Dict with paper and concept counts
        """
        papers_count = self._get_papers_collection().count()
        concepts_count = self._get_concepts_collection().count()

        return {
            "papers": papers_count,
            "concepts": concepts_count,
        }

    def delete_paper(self, arxiv_id: str) -> None:
        """Delete a paper from the vector store.

        Args:
            arxiv_id: Paper to delete
        """
        collection = self._get_papers_collection()
        collection.delete(ids=[arxiv_id])
        logger.info("paper_deleted", arxiv_id=arxiv_id)


# Global client instance
chromadb_client = ChromaDBClient()
