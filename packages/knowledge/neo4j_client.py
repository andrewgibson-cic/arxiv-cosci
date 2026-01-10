"""Neo4j client and schema management.

Provides async Neo4j operations for the arxiv-cosci knowledge graph:
- Paper nodes with metadata and embeddings
- Author nodes with paper relationships
- Citation edges with intent classification
- Category nodes for organization
"""

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from packages.ingestion.models import ParsedPaper, Citation, CitationIntent

logger = structlog.get_logger()


class Neo4jClient:
    """Async Neo4j client wrapper."""

    def __init__(self, uri: str | None = None, auth: tuple[str, str] | None = None) -> None:
        """Initialize Neo4j client.

        Args:
            uri: Bolt URI (default: bolt://127.0.0.1:7687)
            auth: Tuple of (username, password) (default: ("neo4j", "password"))
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        self.auth = auth or (
            os.getenv("NEO4J_USER", "neo4j"),
            os.getenv("NEO4J_PASSWORD", "password"),
        )
        self.driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Establish connection to Neo4j."""
        if not self.driver:
            try:
                self.driver = AsyncGraphDatabase.driver(self.uri, auth=self.auth)
                await self.driver.verify_connectivity()
                logger.info("neo4j_connected", uri=self.uri)
            except Exception as e:
                logger.error("neo4j_connection_failed", error=str(e))
                raise

    async def close(self) -> None:
        """Close connection."""
        if self.driver:
            await self.driver.close()
            self.driver = None
            logger.info("neo4j_closed")

    async def verify_connection(self) -> bool:
        """Verify the connection to Neo4j is working.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            if not self.driver:
                await self.connect()
            
            assert self.driver is not None
            await self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error("connection_verification_failed", error=str(e))
            return False

    async def execute_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results as a list of dicts.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        async with self.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async session context."""
        if not self.driver:
            await self.connect()

        # driver is definitely not None here due to connect()
        assert self.driver is not None 

        async with self.driver.session() as session:
            yield session

    async def init_schema(self) -> None:
        """Initialize database constraints and indexes."""
        constraints = [
            # Paper constraints
            "CREATE CONSTRAINT paper_arxiv_id_unique IF NOT EXISTS FOR (p:Paper) REQUIRE p.arxiv_id IS UNIQUE",
            "CREATE INDEX paper_category_index IF NOT EXISTS FOR (p:Paper) ON (p.primary_category)",
            "CREATE INDEX paper_published_index IF NOT EXISTS FOR (p:Paper) ON (p.published)",
            
            # Author constraints
            "CREATE CONSTRAINT author_name_unique IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE",
            
            # Category constraints
            "CREATE CONSTRAINT category_id_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.id IS UNIQUE",
            
            # Concept constraints
            "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
            "CREATE INDEX concept_type_index IF NOT EXISTS FOR (c:Concept) ON (c.type)",
        ]

        async with self.session() as session:
            for query in constraints:
                try:
                    await session.run(query)
                    logger.info("schema_updated", query=query)
                except Exception as e:
                    logger.error("schema_update_failed", query=query, error=str(e))
                    raise


    async def ingest_paper(self, paper: ParsedPaper) -> str:
        """Ingest a parsed paper into the graph.

        Creates:
        - Paper node with metadata
        - Author nodes and AUTHORED_BY relationships
        - Category nodes and BELONGS_TO relationships

        Args:
            paper: Parsed paper with extracted content

        Returns:
            The arxiv_id of the ingested paper
        """
        query = """
        MERGE (p:Paper {arxiv_id: $arxiv_id})
        SET p.title = $title,
            p.abstract = $abstract,
            p.full_text = $full_text,
            p.primary_category = $primary_category,
            p.published = $published,
            p.parser_used = $parser_used,
            p.parse_confidence = $parse_confidence,
            p.equation_count = $equation_count,
            p.citation_count = $citation_count,
            p.section_count = $section_count

        WITH p
        UNWIND $authors AS author_name
        MERGE (a:Author {name: author_name})
        MERGE (a)-[:AUTHORED]->(p)

        WITH p
        UNWIND $categories AS cat_id
        MERGE (c:Category {id: cat_id})
        MERGE (p)-[:BELONGS_TO]->(c)

        RETURN p.arxiv_id AS arxiv_id
        """

        params = {
            "arxiv_id": paper.arxiv_id,
            "title": paper.title,
            "abstract": paper.abstract,
            "full_text": paper.full_text[:50000] if paper.full_text else "",  # Limit text size
            "primary_category": paper.categories[0] if paper.categories else "",
            "published": paper.published_date.isoformat() if paper.published_date else None,
            "parser_used": paper.parser_used.value,
            "parse_confidence": paper.parse_confidence,
            "equation_count": len(paper.equations),
            "citation_count": len(paper.citations),
            "section_count": len(paper.sections),
            "authors": paper.authors,
            "categories": paper.categories,
        }

        async with self.session() as session:
            result = await session.run(query, params)
            record = await result.single()
            arxiv_id = record["arxiv_id"] if record else paper.arxiv_id
            logger.info("paper_ingested", arxiv_id=arxiv_id)
            return arxiv_id

    async def ingest_citations(self, paper: ParsedPaper) -> int:
        """Create citation relationships from a paper.

        Creates CITES edges from this paper to cited papers.
        Creates placeholder Paper nodes for papers not yet ingested.

        Args:
            paper: Paper with extracted citations

        Returns:
            Number of citation edges created
        """
        if not paper.citations:
            return 0

        # Filter to citations with arXiv IDs
        arxiv_citations = [c for c in paper.citations if c.arxiv_id]

        if not arxiv_citations:
            return 0

        query = """
        MATCH (source:Paper {arxiv_id: $source_id})
        UNWIND $citations AS cit
        MERGE (target:Paper {arxiv_id: cit.arxiv_id})
        MERGE (source)-[r:CITES]->(target)
        SET r.intent = cit.intent,
            r.context = cit.context
        RETURN count(r) AS count
        """

        citations_data = [
            {
                "arxiv_id": c.arxiv_id,
                "intent": c.intent.value,
                "context": c.context[:500] if c.context else "",
            }
            for c in arxiv_citations
        ]

        async with self.session() as session:
            result = await session.run(
                query,
                {"source_id": paper.arxiv_id, "citations": citations_data},
            )
            record = await result.single()
            count = record["count"] if record else 0
            logger.info("citations_ingested", arxiv_id=paper.arxiv_id, count=count)
            return count

    async def ingest_batch(
        self,
        papers: list[ParsedPaper],
        *,
        include_citations: bool = True,
    ) -> dict[str, int]:
        """Ingest multiple papers efficiently.

        Args:
            papers: List of parsed papers
            include_citations: Whether to also create citation edges

        Returns:
            Stats dict with papers_ingested and citations_created counts
        """
        papers_ingested = 0
        citations_created = 0

        for paper in papers:
            try:
                await self.ingest_paper(paper)
                papers_ingested += 1

                if include_citations:
                    citations_created += await self.ingest_citations(paper)

            except Exception as e:
                logger.error("ingest_failed", arxiv_id=paper.arxiv_id, error=str(e))

        logger.info(
            "batch_ingest_complete",
            papers=papers_ingested,
            citations=citations_created,
        )
        return {"papers_ingested": papers_ingested, "citations_created": citations_created}

    async def get_paper(self, arxiv_id: str) -> dict[str, Any] | None:
        """Get a paper by arxiv_id.

        Args:
            arxiv_id: The arXiv identifier

        Returns:
            Paper data dict or None if not found
        """
        query = """
        MATCH (p:Paper {arxiv_id: $arxiv_id})
        OPTIONAL MATCH (a:Author)-[:AUTHORED]->(p)
        OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
        RETURN p {
            .*,
            authors: collect(DISTINCT a.name),
            categories: collect(DISTINCT c.id)
        } AS paper
        """

        async with self.session() as session:
            result = await session.run(query, {"arxiv_id": arxiv_id})
            record = await result.single()
            return dict(record["paper"]) if record else None

    async def get_citation_network(
        self,
        arxiv_id: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """Get the citation network around a paper.

        Args:
            arxiv_id: Central paper's arXiv ID
            depth: How many hops to traverse (1-3 recommended)

        Returns:
            Dict with nodes and edges lists
        """
        query = """
        MATCH path = (p:Paper {arxiv_id: $arxiv_id})-[:CITES*1..$depth]-(related:Paper)
        WITH nodes(path) AS papers, relationships(path) AS rels
        UNWIND papers AS paper
        WITH collect(DISTINCT paper {.arxiv_id, .title}) AS nodes,
             rels
        UNWIND rels AS rel
        WITH nodes, collect(DISTINCT {
            source: startNode(rel).arxiv_id,
            target: endNode(rel).arxiv_id,
            intent: rel.intent
        }) AS edges
        RETURN nodes, edges
        """

        async with self.session() as session:
            result = await session.run(query, {"arxiv_id": arxiv_id, "depth": depth})
            record = await result.single()
            if record:
                return {"nodes": record["nodes"], "edges": record["edges"]}
            return {"nodes": [], "edges": []}

    async def get_stats(self) -> dict[str, int]:
        """Get database statistics.

        Returns:
            Dict with node and edge counts
        """
        query = """
        MATCH (p:Paper) WITH count(p) AS papers
        MATCH (a:Author) WITH papers, count(a) AS authors
        MATCH (c:Category) WITH papers, authors, count(c) AS categories
        MATCH ()-[r:CITES]->() WITH papers, authors, categories, count(r) AS citations
        MATCH ()-[r:AUTHORED]->() WITH papers, authors, categories, citations, count(r) AS authorships
        RETURN papers, authors, categories, citations, authorships
        """

        async with self.session() as session:
            result = await session.run(query)
            record = await result.single()
            if record:
                return dict(record)
            return {"papers": 0, "authors": 0, "categories": 0, "citations": 0, "authorships": 0}


# Global client instance
neo4j_client = Neo4jClient()
