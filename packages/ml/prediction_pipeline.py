"""
Link Prediction Pipeline - Integrates GraphSAGE with Knowledge Graph

This module provides end-to-end pipeline for training link prediction models
on citation networks and generating predictions.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
from torch_geometric.data import Data
from sentence_transformers import SentenceTransformer

from packages.knowledge.neo4j_client import Neo4jClient
from packages.knowledge.chromadb_client import ChromaDBClient
from packages.ml.link_predictor import LinkPredictor

logger = logging.getLogger(__name__)


class LinkPredictionPipeline:
    """
    End-to-end pipeline for link prediction on citation networks.
    
    Features:
    - Load graph data from Neo4j
    - Use embeddings from ChromaDB or generate new ones
    - Train GraphSAGE model
    - Generate predictions
    - Store results back to Neo4j
    """
    
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        chroma_client: Optional[ChromaDBClient] = None,
        embedding_model: str = "sentence-transformers/all-mpnet-base-v2",
    ):
        """
        Initialize link prediction pipeline.
        
        Args:
            neo4j_client: Neo4j client for graph data
            chroma_client: ChromaDB client for embeddings (optional)
            embedding_model: SentenceTransformer model name
        """
        self.neo4j = neo4j_client
        self.chroma = chroma_client
        self.embedding_model_name = embedding_model
        self.embedder = SentenceTransformer(embedding_model)
        self.predictor: Optional[LinkPredictor] = None
        
        logger.info(f"Initialized pipeline with embedding model: {embedding_model}")
    
    async def load_graph_data(
        self,
        node_limit: Optional[int] = None,
        include_concepts: bool = False,
    ) -> Data:
        """
        Load graph data from Neo4j into PyTorch Geometric format.
        
        Args:
            node_limit: Limit number of papers (None = all)
            include_concepts: Include concept nodes (not just papers)
            
        Returns:
            PyG Data object with node features and edges
        """
        logger.info("Loading graph data from Neo4j...")
        
        # Get papers and their embeddings
        papers_query = """
        MATCH (p:Paper)
        RETURN p.arxiv_id AS arxiv_id,
               p.title AS title,
               p.abstract AS abstract,
               p.embedding AS embedding
        ORDER BY p.published_date DESC
        """ + (f"LIMIT {node_limit}" if node_limit else "")
        
        papers = []
        arxiv_id_to_idx = {}
        
        async with self.neo4j.driver.session() as session:
            result = await session.run(papers_query)
            
            idx = 0
            async for record in result:
                arxiv_id = record["arxiv_id"]
                arxiv_id_to_idx[arxiv_id] = idx
                
                # Get or generate embedding
                embedding = record.get("embedding")
                if embedding is None:
                    # Generate embedding from title + abstract
                    text = f"{record['title']} {record['abstract']}"
                    embedding = self.embedder.encode(text).tolist()
                
                papers.append({
                    "arxiv_id": arxiv_id,
                    "embedding": embedding,
                })
                idx += 1
        
        logger.info(f"Loaded {len(papers)} papers")
        
        # Get citation edges
        edges_query = """
        MATCH (p1:Paper)-[:CITES]->(p2:Paper)
        WHERE p1.arxiv_id IN $arxiv_ids
          AND p2.arxiv_id IN $arxiv_ids
        RETURN p1.arxiv_id AS source, p2.arxiv_id AS target
        """
        
        edges = []
        
        async with self.neo4j.driver.session() as session:
            result = await session.run(
                edges_query,
                arxiv_ids=list(arxiv_id_to_idx.keys()),
            )
            
            async for record in result:
                source_idx = arxiv_id_to_idx.get(record["source"])
                target_idx = arxiv_id_to_idx.get(record["target"])
                
                if source_idx is not None and target_idx is not None:
                    edges.append([source_idx, target_idx])
        
        logger.info(f"Loaded {len(edges)} citation edges")
        
        # Convert to PyTorch tensors
        x = torch.tensor(
            [p["embedding"] for p in papers],
            dtype=torch.float,
        )
        
        if edges:
            edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
        else:
            # Empty edge index
            edge_index = torch.empty((2, 0), dtype=torch.long)
        
        # Create PyG Data object
        data = Data(
            x=x,
            edge_index=edge_index,
            num_nodes=len(papers),
        )
        
        # Store mapping for later use
        self.arxiv_id_to_idx = arxiv_id_to_idx
        self.idx_to_arxiv_id = {v: k for k, v in arxiv_id_to_idx.items()}
        
        logger.info(
            f"Created graph: {data.num_nodes} nodes, "
            f"{data.edge_index.size(1)} edges, "
            f"feature dim: {data.x.size(1)}"
        )
        
        return data
    
    async def train(
        self,
        data: Data,
        epochs: int = 100,
        hidden_channels: int = 256,
        out_channels: int = 128,
        learning_rate: float = 0.001,
        patience: int = 10,
        checkpoint_dir: Optional[Path] = None,
    ) -> Dict[str, List[float]]:
        """
        Train link prediction model.
        
        Args:
             PyG Data object with graph
            epochs: Number of training epochs
            hidden_channels: Hidden layer dimension
            out_channels: Output embedding dimension
            learning_rate: Learning rate
            patience: Early stopping patience
            checkpoint_dir: Directory to save checkpoints
            
        Returns:
            Training history
        """
        logger.info("Training link prediction model...")
        
        # Initialize predictor
        self.predictor = LinkPredictor(
            in_channels=data.x.size(1),
            hidden_channels=hidden_channels,
            out_channels=out_channels,
            learning_rate=learning_rate,
        )
        
        # Train model
        history = self.predictor.fit(
            data=data,
            epochs=epochs,
            patience=patience,
            checkpoint_dir=checkpoint_dir,
        )
        
        logger.info("Training complete!")
        
        return history
    
    async def predict_missing_citations(
        self,
        data: Data,
        source_arxiv_ids: Optional[List[str]] = None,
        top_k: int = 100,
        min_score: float = 0.5,
    ) -> List[Dict[str, any]]:
        """
        Predict missing citations between papers.
        
        Args:
             Graph data
            source_arxiv_ids: Papers to predict from (None = all)
            top_k: Maximum predictions per paper
            min_score: Minimum prediction score
            
        Returns:
            List of prediction dictionaries
        """
        if self.predictor is None:
            raise ValueError("Model not trained. Call train() first.")
        
        logger.info("Generating link predictions...")
        
        # Convert arxiv IDs to indices
        if source_arxiv_ids:
            source_nodes = [
                self.arxiv_id_to_idx[aid]
                for aid in source_arxiv_ids
                if aid in self.arxiv_id_to_idx
            ]
        else:
            source_nodes = None
        
        # Generate predictions
        raw_predictions = self.predictor.predict_links(
            data=data,
            source_nodes=source_nodes,
            top_k=top_k,
        )
        
        # Filter and format
        predictions = []
        
        for source_idx, target_idx, score in raw_predictions:
            if score >= min_score:
                predictions.append({
                    "source_arxiv_id": self.idx_to_arxiv_id[source_idx],
                    "target_arxiv_id": self.idx_to_arxiv_id[target_idx],
                    "score": float(score),
                    "source_idx": source_idx,
                    "target_idx": target_idx,
                })
        
        logger.info(f"Generated {len(predictions)} predictions (score >= {min_score})")
        
        return predictions
    
    async def store_predictions(
        self,
        predictions: List[Dict[str, any]],
        relationship_type: str = "PREDICTED_CITATION",
    ) -> int:
        """
        Store predictions in Neo4j as potential citation edges.
        
        Args:
            predictions: List of prediction dictionaries
            relationship_type: Neo4j relationship type
            
        Returns:
            Number of relationships created
        """
        logger.info(f"Storing {len(predictions)} predictions in Neo4j...")
        
        query = f"""
        UNWIND $predictions AS pred
        MATCH (source:Paper {{arxiv_id: pred.source_arxiv_id}})
        MATCH (target:Paper {{arxiv_id: pred.target_arxiv_id}})
        MERGE (source)-[r:{relationship_type}]->(target)
        SET r.score = pred.score,
            r.predicted_at = datetime()
        RETURN COUNT(r) AS created
        """
        
        async with self.neo4j.driver.session() as session:
            result = await session.run(query, predictions=predictions)
            record = await result.single()
            created = record["created"] if record else 0
        
        logger.info(f"Created {created} prediction relationships")
        
        return created
    
    async def evaluate_predictions(
        self,
        predictions: List[Dict[str, any]],
    ) -> Dict[str, float]:
        """
        Evaluate predictions against actual citations (if available).
        
        Args:
            predictions: List of predictions
            
        Returns:
            Evaluation metrics
        """
        logger.info("Evaluating predictions...")
        
        # Get actual citations for the predicted pairs
        query = """
        UNWIND $pairs AS pair
        MATCH (source:Paper {arxiv_id: pair.source})
        OPTIONAL MATCH (source)-[:CITES]->(target:Paper {arxiv_id: pair.target})
        RETURN pair.source AS source,
               pair.target AS target,
               CASE WHEN target IS NOT NULL THEN 1 ELSE 0 END AS exists
        """
        
        pairs = [
            {"source": p["source_arxiv_id"], "target": p["target_arxiv_id"]}
            for p in predictions
        ]
        
        results = []
        
        async with self.neo4j.driver.session() as session:
            result = await session.run(query, pairs=pairs)
            
            async for record in result:
                results.append(record["exists"])
        
        # Calculate metrics
        if not results:
            return {"precision": 0.0, "coverage": 0.0}
        
        true_positives = sum(results)
        precision = true_positives / len(results) if results else 0.0
        
        # Coverage: how many of our predictions are novel (not in graph)
        novel = len(results) - true_positives
        coverage = novel / len(results) if results else 0.0
        
        metrics = {
            "precision": precision,
            "coverage": coverage,
            "total_predictions": len(results),
            "true_positives": true_positives,
            "novel_predictions": novel,
        }
        
        logger.info(f"Evaluation: Precision={precision:.2%}, Coverage={coverage:.2%}")
        
        return metrics
    
    async def run_full_pipeline(
        self,
        node_limit: Optional[int] = 1000,
        epochs: int = 50,
        top_k: int = 20,
        min_score: float = 0.6,
        checkpoint_dir: Optional[Path] = None,
        store_results: bool = True,
    ) -> Dict[str, any]:
        """
        Run complete link prediction pipeline.
        
        Args:
            node_limit: Limit papers for training
            epochs: Training epochs
            top_k: Predictions per paper
            min_score: Minimum score threshold
            checkpoint_dir: Model checkpoint directory
            store_results: Store predictions in Neo4j
            
        Returns:
            Pipeline results and metrics
        """
        logger.info("Starting full link prediction pipeline...")
        
        # Step 1: Load data
        data = await self.load_graph_data(node_limit=node_limit)
        
        # Step 2: Train model
        history = await self.train(
            data=data,
            epochs=epochs,
            checkpoint_dir=checkpoint_dir,
        )
        
        # Step 3: Generate predictions
        predictions = await self.predict_missing_citations(
            data=data,
            top_k=top_k,
            min_score=min_score,
        )
        
        # Step 4: Evaluate
        metrics = await self.evaluate_predictions(predictions)
        
        # Step 5: Store results
        stored = 0
        if store_results and predictions:
            stored = await self.store_predictions(predictions)
        
        results = {
            "training_history": history,
            "predictions": predictions,
            "metrics": metrics,
            "stored_count": stored,
            "graph_stats": {
                "num_nodes": data.num_nodes,
                "num_edges": data.edge_index.size(1),
                "feature_dim": data.x.size(1),
            },
        }
        
        logger.info("Pipeline complete!")
        logger.info(f"  - Trained on {data.num_nodes} papers")
        logger.info(f"  - Generated {len(predictions)} predictions")
        logger.info(f"  - Precision: {metrics.get('precision', 0):.2%}")
        logger.info(f"  - Stored: {stored} relationships")
        
        return results
    
    def save_model(self, path: Path) -> None:
        """Save trained model."""
        if self.predictor is None:
            raise ValueError("No model to save")
        self.predictor.save(path)
    
    def load_model(self, path: Path) -> None:
        """Load trained model."""
        # Initialize predictor with default params (will be overwritten)
        self.predictor = LinkPredictor()
        self.predictor.load(path)