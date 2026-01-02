"""Neo4j client and schema management."""

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

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


# Global client instance
neo4j_client = Neo4jClient()
