"""Neo4j index optimization utilities.

Provides tools for creating, managing, and optimizing Neo4j indexes
for improved query performance.
"""

import asyncio
from typing import Any

import structlog

from packages.knowledge.neo4j_client import neo4j_client

logger = structlog.get_logger()


class IndexOptimizer:
    """Utility for optimizing Neo4j indexes."""

    def __init__(self) -> None:
        """Initialize index optimizer."""
        self.client = neo4j_client

    async def create_recommended_indexes(self) -> dict[str, list[str]]:
        """Create all recommended indexes for optimal query performance.

        Returns:
            Dictionary with created indexes by type
        """
        await self.client.connect()

        try:
            created_indexes = {
                "single_property": [],
                "composite": [],
                "fulltext": [],
            }

            # Single property indexes
            single_indexes = [
                ("Paper", "arxiv_id"),
                ("Paper", "published_date"),
                ("Paper", "s2_id"),
                ("Author", "name"),
                ("Category", "id"),
                ("Concept", "name"),
                ("Concept", "type"),
            ]

            for label, property in single_indexes:
                try:
                    await self._create_index(label, [property])
                    created_indexes["single_property"].append(f"{label}.{property}")
                    logger.info("index_created", label=label, property=property)
                except Exception as e:
                    logger.warning("index_creation_failed", label=label, property=property, error=str(e))

            # Composite indexes for common query patterns
            composite_indexes = [
                ("Paper", ["primary_category", "published_date"]),
                ("Paper", ["primary_category", "arxiv_id"]),
                ("CITES", ["intent", "position"]),
            ]

            for label, properties in composite_indexes:
                try:
                    await self._create_composite_index(label, properties)
                    created_indexes["composite"].append(f"{label}.{'+'.join(properties)}")
                    logger.info("composite_index_created", label=label, properties=properties)
                except Exception as e:
                    logger.warning("composite_index_failed", label=label, properties=properties, error=str(e))

            # Full-text search indexes
            fulltext_indexes = [
                ("papers_fulltext", ["Paper"], ["title", "abstract", "full_text"]),
                ("concepts_fulltext", ["Concept"], ["name"]),
            ]

            for name, labels, properties in fulltext_indexes:
                try:
                    await self._create_fulltext_index(name, labels, properties)
                    created_indexes["fulltext"].append(name)
                    logger.info("fulltext_index_created", name=name)
                except Exception as e:
                    logger.warning("fulltext_index_failed", name=name, error=str(e))

            return created_indexes

        finally:
            await self.client.close()

    async def _create_index(self, label: str, properties: list[str]) -> None:
        """Create a single or composite property index."""
        index_name = f"idx_{label.lower()}_{'_'.join(properties)}"
        properties_str = ", ".join(f"n.{p}" for p in properties)

        query = f"""
        CREATE INDEX {index_name} IF NOT EXISTS
        FOR (n:{label})
        ON ({properties_str})
        """

        async with self.client.session() as session:
            await session.run(query)

    async def _create_composite_index(self, label: str, properties: list[str]) -> None:
        """Create a composite index."""
        await self._create_index(label, properties)

    async def _create_fulltext_index(
        self,
        name: str,
        labels: list[str],
        properties: list[str],
    ) -> None:
        """Create a full-text search index."""
        labels_str = "|".join(labels)
        properties_list = ", ".join(f'"{p}"' for p in properties)

        query = f"""
        CREATE FULLTEXT INDEX {name} IF NOT EXISTS
        FOR (n:{labels_str})
        ON EACH [{properties_list}]
        """

        async with self.client.session() as session:
            await session.run(query)

    async def list_indexes(self) -> list[dict[str, Any]]:
        """List all existing indexes.

        Returns:
            List of index information dictionaries
        """
        await self.client.connect()

        try:
            query = "SHOW INDEXES"

            async with self.client.session() as session:
                result = await session.run(query)
                records = await result.data()

            return [
                {
                    "name": r.get("name"),
                    "type": r.get("type"),
                    "labels": r.get("labelsOrTypes", []),
                    "properties": r.get("properties", []),
                    "state": r.get("state"),
                    "population_percent": r.get("populationPercent", 0),
                }
                for r in records
            ]

        finally:
            await self.client.close()

    async def analyze_query_performance(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyze query performance and suggest optimizations.

        Args:
            query: Cypher query to analyze
            params: Query parameters

        Returns:
            Performance analysis with suggestions
        """
        await self.client.connect()

        try:
            # Get query plan
            explain_query = f"EXPLAIN {query}"

            async with self.client.session() as session:
                result = await session.run(explain_query, params or {})
                plan = await result.consume()

            # Analyze plan for optimization opportunities
            analysis = {
                "query": query,
                "db_hits": getattr(plan.result_consumed_after, "db_hits", 0),
                "suggestions": [],
            }

            # Check for missing indexes
            if "NodeByLabelScan" in str(plan):
                analysis["suggestions"].append(
                    "Consider adding an index on frequently filtered properties"
                )

            # Check for cartesian products
            if "CartesianProduct" in str(plan):
                analysis["suggestions"].append(
                    "Query contains cartesian product - consider adding relationship constraints"
                )

            # Check for eager operations
            if "Eager" in str(plan):
                analysis["suggestions"].append(
                    "Query contains eager operations - may impact memory usage"
                )

            return analysis

        finally:
            await self.client.close()

    async def optimize_database(self) -> dict[str, Any]:
        """Run comprehensive database optimization.

        Returns:
            Optimization results
        """
        await self.client.connect()

        try:
            results = {
                "indexes_created": await self.create_recommended_indexes(),
                "statistics_analyzed": False,
                "constraints_verified": False,
            }

            # Analyze database statistics
            try:
                async with self.client.session() as session:
                    await session.run("CALL db.stats.retrieve('GRAPH COUNTS')")
                results["statistics_analyzed"] = True
                logger.info("database_statistics_analyzed")
            except Exception as e:
                logger.warning("statistics_analysis_failed", error=str(e))

            # Verify constraints
            try:
                constraints = await self._list_constraints()
                results["constraints_verified"] = True
                results["constraints_count"] = len(constraints)
                logger.info("constraints_verified", count=len(constraints))
            except Exception as e:
                logger.warning("constraint_verification_failed", error=str(e))

            return results

        finally:
            await self.client.close()

    async def _list_constraints(self) -> list[dict[str, Any]]:
        """List all database constraints."""
        query = "SHOW CONSTRAINTS"

        async with self.client.session() as session:
            result = await session.run(query)
            records = await result.data()

        return [
            {
                "name": r.get("name"),
                "type": r.get("type"),
                "labels": r.get("labelsOrTypes", []),
                "properties": r.get("properties", []),
            }
            for r in records
        ]

    async def drop_unused_indexes(self, dry_run: bool = True) -> list[str]:
        """Drop indexes that are never used.

        Args:
            dry_run: If True, only list indexes that would be dropped

        Returns:
            List of dropped (or would-be-dropped) index names
        """
        await self.client.connect()

        try:
            # Get index usage statistics
            query = """
            CALL db.stats.retrieve('INDEX USAGE')
            YIELD data
            RETURN data
            """

            async with self.client.session() as session:
                result = await session.run(query)
                records = await result.data()

            # Find unused indexes
            unused_indexes = []
            for record in records:
                data = record.get("data", {})
                if data.get("usageCount", 0) == 0:
                    index_name = data.get("indexName")
                    if index_name and not index_name.startswith("__"):
                        unused_indexes.append(index_name)

            if not dry_run and unused_indexes:
                for index_name in unused_indexes:
                    try:
                        async with self.client.session() as session:
                            await session.run(f"DROP INDEX {index_name}")
                        logger.info("index_dropped", name=index_name)
                    except Exception as e:
                        logger.warning("index_drop_failed", name=index_name, error=str(e))

            return unused_indexes

        finally:
            await self.client.close()


# Global optimizer instance
index_optimizer = IndexOptimizer()


async def optimize_neo4j_indexes() -> dict[str, Any]:
    """Convenience function to optimize all Neo4j indexes.

    Returns:
        Optimization results
    """
    return await index_optimizer.optimize_database()