"""
Structural Hole Detection in Citation Networks

This module identifies gaps in the knowledge graph where connections between
concepts, papers, or research areas should exist but don't. These "structural holes"
represent potential research opportunities and hypothesis generation targets.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx
from neo4j import AsyncDriver

logger = logging.getLogger(__name__)


@dataclass
class StructuralHole:
    """
    Represents a structural hole in the knowledge graph.
    
    A structural hole is a gap between two or more nodes/clusters that
    should be connected based on their properties but currently aren't.
    """
    
    source_id: str
    target_id: str
    source_type: str  # "Paper" or "Concept"
    target_type: str
    source_name: str
    target_name: str
    score: float
    shared_neighbors: List[str]
    reason: str
    metadata: Dict[str, any]


class StructuralHoleDetector:
    """
    Detect structural holes (missing connections) in citation networks.
    
    Methods:
    - Shared neighbor analysis: Papers/concepts with many common neighbors
    - Community bridging: Nodes that could bridge disconnected communities
    - Temporal gaps: Recent papers that don't cite relevant older work
    - Cross-domain gaps: Related concepts in different subfields
    """
    
    def __init__(self, neo4j_driver: AsyncDriver):
        """
        Initialize structural hole detector.
        
        Args:
            neo4j_driver: Neo4j async driver instance
        """
        self.driver = neo4j_driver
    
    async def find_paper_gaps(
        self,
        min_shared_neighbors: int = 3,
        max_distance: int = 2,
        limit: int = 100,
    ) -> List[StructuralHole]:
        """
        Find papers that should cite each other but don't.
        
        Uses shared neighbor analysis: papers with many mutual citations
        but no direct citation relationship.
        
        Args:
            min_shared_neighbors: Minimum number of shared neighbors
            max_distance: Maximum hop distance to consider
            limit: Maximum number of results
            
        Returns:
            List of structural holes between papers
        """
        query = """
        MATCH (p1:Paper)-[:CITES]->(shared:Paper)<-[:CITES]-(p2:Paper)
        WHERE p1 <> p2
          AND NOT (p1)-[:CITES]->(p2)
          AND NOT (p2)-[:CITES]->(p1)
        WITH p1, p2, COUNT(DISTINCT shared) AS shared_count,
             COLLECT(DISTINCT shared.title)[0..5] AS shared_papers
        WHERE shared_count >= $min_shared
        RETURN p1.arxiv_id AS source_id,
               p2.arxiv_id AS target_id,
               p1.title AS source_title,
               p2.title AS target_title,
               shared_count,
               shared_papers,
               p1.published_date AS source_date,
               p2.published_date AS target_date
        ORDER BY shared_count DESC
        LIMIT $limit
        """
        
        holes = []
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                min_shared=min_shared_neighbors,
                limit=limit,
            )
            
            async for record in result:
                # Calculate score based on shared neighbors
                score = record["shared_count"] / (min_shared_neighbors + 10)
                score = min(1.0, score)
                
                holes.append(
                    StructuralHole(
                        source_id=record["source_id"],
                        target_id=record["target_id"],
                        source_type="Paper",
                        target_type="Paper",
                        source_name=record["source_title"],
                        target_name=record["target_title"],
                        score=score,
                        shared_neighbors=record["shared_papers"],
                        reason=f"Share {record['shared_count']} mutual citations",
                        metadata={
                            "shared_count": record["shared_count"],
                            "source_date": record["source_date"],
                            "target_date": record["target_date"],
                        },
                    )
                )
        
        logger.info(f"Found {len(holes)} paper-to-paper structural holes")
        return holes
    
    async def find_concept_gaps(
        self,
        min_shared_papers: int = 2,
        limit: int = 100,
    ) -> List[StructuralHole]:
        """
        Find concepts that appear in similar papers but aren't connected.
        
        Identifies related concepts that should be linked based on
        co-occurrence in papers.
        
        Args:
            min_shared_papers: Minimum papers mentioning both concepts
            limit: Maximum number of results
            
        Returns:
            List of structural holes between concepts
        """
        query = """
        MATCH (c1:Concept)<-[:MENTIONS]-(p:Paper)-[:MENTIONS]->(c2:Concept)
        WHERE c1 <> c2
          AND c1.name < c2.name  // Avoid duplicates
          AND NOT (c1)-[:RELATED_TO]-(c2)
        WITH c1, c2, COUNT(DISTINCT p) AS shared_papers,
             COLLECT(DISTINCT p.title)[0..5] AS paper_titles
        WHERE shared_papers >= $min_shared
        RETURN c1.name AS source_name,
               c2.name AS target_name,
               c1.type AS source_type_detail,
               c2.type AS target_type_detail,
               shared_papers,
               paper_titles
        ORDER BY shared_papers DESC
        LIMIT $limit
        """
        
        holes = []
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                min_shared=min_shared_papers,
                limit=limit,
            )
            
            async for record in result:
                score = record["shared_papers"] / (min_shared_papers + 5)
                score = min(1.0, score)
                
                holes.append(
                    StructuralHole(
                        source_id=record["source_name"],
                        target_id=record["target_name"],
                        source_type="Concept",
                        target_type="Concept",
                        source_name=record["source_name"],
                        target_name=record["target_name"],
                        score=score,
                        shared_neighbors=record["paper_titles"],
                        reason=f"Co-occur in {record['shared_papers']} papers",
                        metadata={
                            "shared_papers": record["shared_papers"],
                            "source_concept_type": record["source_type_detail"],
                            "target_concept_type": record["target_type_detail"],
                        },
                    )
                )
        
        logger.info(f"Found {len(holes)} concept-to-concept structural holes")
        return holes
    
    async def find_temporal_gaps(
        self,
        year_threshold: int = 2,
        min_relevance: int = 2,
        limit: int = 100,
    ) -> List[StructuralHole]:
        """
        Find recent papers that don't cite relevant older work.
        
        Identifies papers published recently that should cite older papers
        based on shared concepts/topics but don't.
        
        Args:
            year_threshold: Minimum year difference between papers
            min_relevance: Minimum shared concepts for relevance
            limit: Maximum number of results
            
        Returns:
            List of temporal gaps (missing citations to older work)
        """
        query = """
        MATCH (newer:Paper)-[:MENTIONS]->(c:Concept)<-[:MENTIONS]-(older:Paper)
        WHERE newer.published_date > older.published_date
          AND duration.between(
                date(older.published_date),
                date(newer.published_date)
              ).years >= $year_threshold
          AND NOT (newer)-[:CITES]->(older)
        WITH newer, older, COUNT(DISTINCT c) AS shared_concepts,
             COLLECT(DISTINCT c.name)[0..5] AS concept_names
        WHERE shared_concepts >= $min_relevance
        RETURN newer.arxiv_id AS source_id,
               older.arxiv_id AS target_id,
               newer.title AS source_title,
               older.title AS target_title,
               newer.published_date AS newer_date,
               older.published_date AS older_date,
               shared_concepts,
               concept_names
        ORDER BY shared_concepts DESC, newer_date DESC
        LIMIT $limit
        """
        
        holes = []
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                year_threshold=year_threshold,
                min_relevance=min_relevance,
                limit=limit,
            )
            
            async for record in result:
                score = record["shared_concepts"] / (min_relevance + 5)
                score = min(1.0, score)
                
                holes.append(
                    StructuralHole(
                        source_id=record["source_id"],
                        target_id=record["target_id"],
                        source_type="Paper",
                        target_type="Paper",
                        source_name=record["source_title"],
                        target_name=record["target_title"],
                        score=score,
                        shared_neighbors=record["concept_names"],
                        reason=f"Newer paper doesn't cite relevant older work (shared {record['shared_concepts']} concepts)",
                        metadata={
                            "newer_date": record["newer_date"],
                            "older_date": record["older_date"],
                            "shared_concepts": record["shared_concepts"],
                            "gap_type": "temporal",
                        },
                    )
                )
        
        logger.info(f"Found {len(holes)} temporal gaps")
        return holes
    
    async def find_cross_domain_gaps(
        self,
        min_shared_concepts: int = 1,
        limit: int = 100,
    ) -> List[StructuralHole]:
        """
        Find papers from different domains that share concepts but don't cite each other.
        
        Identifies potential cross-pollination opportunities between subfields.
        
        Args:
            min_shared_concepts: Minimum shared concepts
            limit: Maximum number of results
            
        Returns:
            List of cross-domain gaps
        """
        query = """
        MATCH (p1:Paper)-[:MENTIONS]->(c:Concept)<-[:MENTIONS]-(p2:Paper)
        WHERE p1 <> p2
          AND NOT (p1)-[:CITES]->(p2)
          AND NOT (p2)-[:CITES]->(p1)
          AND p1.categories[0] <> p2.categories[0]  // Different primary categories
        WITH p1, p2, COUNT(DISTINCT c) AS shared_concepts,
             COLLECT(DISTINCT c.name)[0..5] AS concept_names
        WHERE shared_concepts >= $min_shared
        RETURN p1.arxiv_id AS source_id,
               p2.arxiv_id AS target_id,
               p1.title AS source_title,
               p2.title AS target_title,
               p1.categories[0] AS source_category,
               p2.categories[0] AS target_category,
               shared_concepts,
               concept_names
        ORDER BY shared_concepts DESC
        LIMIT $limit
        """
        
        holes = []
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                min_shared=min_shared_concepts,
                limit=limit,
            )
            
            async for record in result:
                score = record["shared_concepts"] / (min_shared_concepts + 3)
                score = min(1.0, score)
                
                holes.append(
                    StructuralHole(
                        source_id=record["source_id"],
                        target_id=record["target_id"],
                        source_type="Paper",
                        target_type="Paper",
                        source_name=record["source_title"],
                        target_name=record["target_title"],
                        score=score,
                        shared_neighbors=record["concept_names"],
                        reason=f"Cross-domain gap: {record['source_category']} ↔ {record['target_category']}",
                        metadata={
                            "source_category": record["source_category"],
                            "target_category": record["target_category"],
                            "shared_concepts": record["shared_concepts"],
                            "gap_type": "cross_domain",
                        },
                    )
                )
        
        logger.info(f"Found {len(holes)} cross-domain gaps")
        return holes
    
    async def find_all_gaps(
        self,
        include_papers: bool = True,
        include_concepts: bool = True,
        include_temporal: bool = True,
        include_cross_domain: bool = True,
        limit_per_type: int = 50,
    ) -> Dict[str, List[StructuralHole]]:
        """
        Find all types of structural holes.
        
        Args:
            include_papers: Include paper-to-paper gaps
            include_concepts: Include concept-to-concept gaps
            include_temporal: Include temporal gaps
            include_cross_domain: Include cross-domain gaps
            limit_per_type: Maximum results per gap type
            
        Returns:
            Dictionary mapping gap type to list of structural holes
        """
        results = {}
        
        if include_papers:
            results["paper_gaps"] = await self.find_paper_gaps(limit=limit_per_type)
        
        if include_concepts:
            results["concept_gaps"] = await self.find_concept_gaps(limit=limit_per_type)
        
        if include_temporal:
            results["temporal_gaps"] = await self.find_temporal_gaps(limit=limit_per_type)
        
        if include_cross_domain:
            results["cross_domain_gaps"] = await self.find_cross_domain_gaps(limit=limit_per_type)
        
        total = sum(len(gaps) for gaps in results.values())
        logger.info(f"Found {total} total structural holes across {len(results)} categories")
        
        return results
    
    def to_networkx_graph(self, holes: List[StructuralHole]) -> nx.Graph:
        """
        Convert structural holes to NetworkX graph for analysis.
        
        Args:
            holes: List of structural holes
            
        Returns:
            NetworkX graph with holes as potential edges
        """
        G = nx.Graph()
        
        for hole in holes:
            # Add nodes with metadata
            G.add_node(
                hole.source_id,
                name=hole.source_name,
                type=hole.source_type,
            )
            G.add_node(
                hole.target_id,
                name=hole.target_name,
                type=hole.target_type,
            )
            
            # Add potential edge with score
            G.add_edge(
                hole.source_id,
                hole.target_id,
                score=hole.score,
                reason=hole.reason,
                shared_neighbors=len(hole.shared_neighbors),
            )
        
        return G
    
    async def get_bridging_potential(
        self,
        node_id: str,
        node_type: str = "Paper",
    ) -> float:
        """
        Calculate how well a node could bridge structural holes.
        
        Measures the betweenness centrality and structural hole spanning
        potential of a given node.
        
        Args:
            node_id: Node identifier (arxiv_id for papers, name for concepts)
            node_type: Type of node ("Paper" or "Concept")
            
        Returns:
            Bridging potential score (0-1)
        """
        if node_type == "Paper":
            query = """
            MATCH (p:Paper {arxiv_id: $node_id})
            OPTIONAL MATCH (p)-[:CITES]->(cited:Paper)
            OPTIONAL MATCH (p)<-[:CITES]-(citing:Paper)
            WITH p, COUNT(DISTINCT cited) AS out_degree,
                 COUNT(DISTINCT citing) AS in_degree
            RETURN out_degree, in_degree,
                   out_degree + in_degree AS total_degree
            """
        else:
            query = """
            MATCH (c:Concept {name: $node_id})
            OPTIONAL MATCH (c)<-[:MENTIONS]-(p:Paper)
            WITH c, COUNT(DISTINCT p) AS paper_count
            RETURN paper_count AS total_degree,
                   paper_count AS out_degree,
                   0 AS in_degree
            """
        
        async with self.driver.session() as session:
            result = await session.run(query, node_id=node_id)
            record = await result.single()
            
            if not record:
                return 0.0
            
            # Simple bridging score based on degree
            # Higher degree = more bridging potential
            total_degree = record["total_degree"]
            score = min(1.0, total_degree / 50.0)  # Normalize to 0-1
            
            return score
