"""
GraphSAGE-based Link Prediction for Citation Networks

This module implements a Graph Neural Network using GraphSAGE for predicting
potential citations between papers and connections between papers and concepts.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn.functional as F
from torch import Tensor, nn
from torch_geometric.data import Data
from torch_geometric.loader import NeighborLoader
from torch_geometric.nn import SAGEConv
from torch_geometric.utils import negative_sampling

logger = logging.getLogger(__name__)


class GraphSAGEModel(nn.Module):
    """
    GraphSAGE model for link prediction in citation networks.
    
    Architecture:
    - 2 GraphSAGE layers with ReLU activation
    - Dropout for regularization
    - Mean aggregation of neighborhood features
    """
    
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        out_channels: int,
        dropout: float = 0.5,
    ):
        """
        Initialize GraphSAGE model.
        
        Args:
            in_channels: Input feature dimension (embedding size)
            hidden_channels: Hidden layer dimension
            out_channels: Output embedding dimension
            dropout: Dropout probability
        """
        super().__init__()
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        self.conv2 = SAGEConv(hidden_channels, out_channels)
        self.dropout = dropout
        
    def forward(self, x: Tensor, edge_index: Tensor) -> Tensor:
        """
        Forward pass through the network.
        
        Args:
            x: Node features [num_nodes, in_channels]
            edge_index: Graph connectivity [2, num_edges]
            
        Returns:
            Node embeddings [num_nodes, out_channels]
        """
        # First GraphSAGE layer
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)
        
        # Second GraphSAGE layer
        x = self.conv2(x, edge_index)
        
        return x
    
    def encode(self, x: Tensor, edge_index: Tensor) -> Tensor:
        """Alias for forward pass (for compatibility)."""
        return self.forward(x, edge_index)
    
    def decode(self, z: Tensor, edge_label_index: Tensor) -> Tensor:
        """
        Decode edge predictions using dot product.
        
        Args:
            z: Node embeddings [num_nodes, out_channels]
            edge_label_index: Edges to predict [2, num_edges]
            
        Returns:
            Edge probabilities [num_edges]
        """
        # Get source and target node embeddings
        src = z[edge_label_index[0]]
        dst = z[edge_label_index[1]]
        
        # Compute dot product and apply sigmoid
        return (src * dst).sum(dim=-1)


class LinkPredictor:
    """
    Link prediction pipeline for citation networks.
    
    Features:
    - Train/test split with negative sampling
    - Early stopping with validation
    - Model checkpointing
    - Prediction scoring and ranking
    """
    
    def __init__(
        self,
        in_channels: int = 768,  # all-mpnet-base-v2 embedding size
        hidden_channels: int = 256,
        out_channels: int = 128,
        dropout: float = 0.3,
        learning_rate: float = 0.001,
        device: Optional[str] = None,
    ):
        """
        Initialize link predictor.
        
        Args:
            in_channels: Input feature dimension
            hidden_channels: Hidden layer dimension
            out_channels: Output embedding dimension
            dropout: Dropout probability
            learning_rate: Learning rate for optimizer
            device: Device to run on ('cpu', 'cuda', 'mps')
        """
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        
        self.device = torch.device(device)
        logger.info(f"Using device: {self.device}")
        
        self.model = GraphSAGEModel(
            in_channels=in_channels,
            hidden_channels=hidden_channels,
            out_channels=out_channels,
            dropout=dropout,
        ).to(self.device)
        
        self.optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=learning_rate,
        )
        
        self.in_channels = in_channels
        self.hidden_channels = hidden_channels
        self.out_channels = out_channels
        
    def prepare_data(
        self,
        data: Data,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
    ) -> Tuple[Data, Data, Data]:
        """
        Split graph data into train/validation/test sets.
        
        Args:
            data: PyG Data object with x (features) and edge_index
            train_ratio: Ratio of edges for training
            val_ratio: Ratio of edges for validation
            
        Returns:
            Tuple of (train_data, val_data, test_data)
        """
        num_edges = data.edge_index.size(1)
        num_train = int(num_edges * train_ratio)
        num_val = int(num_edges * val_ratio)
        
        # Shuffle edges
        perm = torch.randperm(num_edges)
        edge_index = data.edge_index[:, perm]
        
        # Split edges
        train_edge_index = edge_index[:, :num_train]
        val_edge_index = edge_index[:, num_train:num_train + num_val]
        test_edge_index = edge_index[:, num_train + num_val:]
        
        # Create data objects
        train_data = Data(
            x=data.x,
            edge_index=train_edge_index,
            num_nodes=data.num_nodes,
        )
        
        val_data = Data(
            x=data.x,
            edge_index=val_edge_index,
            num_nodes=data.num_nodes,
        )
        
        test_data = Data(
            x=data.x,
            edge_index=test_edge_index,
            num_nodes=data.num_nodes,
        )
        
        return train_data, val_data, test_data
    
    def train_epoch(self, data: Data) -> float:
        """
        Train for one epoch.
        
        Args:
            data: Training data
            
        Returns:
            Average training loss
        """
        self.model.train()
        self.optimizer.zero_grad()
        
        # Move data to device
        x = data.x.to(self.device)
        edge_index = data.edge_index.to(self.device)
        
        # Encode node embeddings
        z = self.model.encode(x, edge_index)
        
        # Positive edges (actual citations)
        pos_edge_index = edge_index
        
        # Negative edges (non-citations)
        neg_edge_index = negative_sampling(
            edge_index=edge_index,
            num_nodes=data.num_nodes,
            num_neg_samples=pos_edge_index.size(1),
        ).to(self.device)
        
        # Compute predictions
        pos_pred = self.model.decode(z, pos_edge_index)
        neg_pred = self.model.decode(z, neg_edge_index)
        
        # Binary cross-entropy loss
        pos_loss = F.binary_cross_entropy_with_logits(
            pos_pred, torch.ones_like(pos_pred)
        )
        neg_loss = F.binary_cross_entropy_with_logits(
            neg_pred, torch.zeros_like(neg_pred)
        )
        loss = pos_loss + neg_loss
        
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
    
    @torch.no_grad()
    def evaluate(self, data: Data) -> Dict[str, float]:
        """
        Evaluate model on validation/test data.
        
        Args:
             Validation or test data
            
        Returns:
            Dictionary with metrics (loss, accuracy, auc)
        """
        self.model.eval()
        
        # Move data to device
        x = data.x.to(self.device)
        edge_index = data.edge_index.to(self.device)
        
        # Encode node embeddings
        z = self.model.encode(x, edge_index)
        
        # Positive and negative edges
        pos_edge_index = edge_index
        neg_edge_index = negative_sampling(
            edge_index=edge_index,
            num_nodes=data.num_nodes,
            num_neg_samples=pos_edge_index.size(1),
        ).to(self.device)
        
        # Compute predictions
        pos_pred = self.model.decode(z, pos_edge_index)
        neg_pred = self.model.decode(z, neg_edge_index)
        
        # Compute loss
        pos_loss = F.binary_cross_entropy_with_logits(
            pos_pred, torch.ones_like(pos_pred)
        )
        neg_loss = F.binary_cross_entropy_with_logits(
            neg_pred, torch.zeros_like(neg_pred)
        )
        loss = (pos_loss + neg_loss).item()
        
        # Compute accuracy
        pred = torch.cat([pos_pred, neg_pred])
        true = torch.cat([
            torch.ones_like(pos_pred),
            torch.zeros_like(neg_pred),
        ])
        accuracy = ((pred > 0) == (true > 0.5)).float().mean().item()
        
        # Compute AUC (simple approximation)
        pred_sorted = torch.cat([pos_pred, neg_pred]).sigmoid().sort(descending=True)[0]
        auc = (pred_sorted[:len(pos_pred)].mean() - pred_sorted[len(pos_pred):].mean()).item()
        auc = (auc + 1) / 2  # Normalize to [0, 1]
        
        return {
            "loss": loss,
            "accuracy": accuracy,
            "auc": max(0.0, min(1.0, auc)),  # Clamp to valid range
        }
    
    def fit(
        self,
        data: Data,
        epochs: int = 100,
        patience: int = 10,
        checkpoint_dir: Optional[Path] = None,
    ) -> Dict[str, List[float]]:
        """
        Train the model with early stopping.
        
        Args:
             Full graph data
            epochs: Maximum number of epochs
            patience: Early stopping patience
            checkpoint_dir: Directory to save checkpoints
            
        Returns:
            Training history
        """
        # Prepare data splits
        train_data, val_data, test_data = self.prepare_data(data)
        
        history = {
            "train_loss": [],
            "val_loss": [],
            "val_accuracy": [],
            "val_auc": [],
        }
        
        best_val_loss = float("inf")
        patience_counter = 0
        
        logger.info(f"Training on {train_data.edge_index.size(1)} edges")
        logger.info(f"Validation on {val_data.edge_index.size(1)} edges")
        
        for epoch in range(epochs):
            # Train
            train_loss = self.train_epoch(train_data)
            history["train_loss"].append(train_loss)
            
            # Validate
            val_metrics = self.evaluate(val_data)
            history["val_loss"].append(val_metrics["loss"])
            history["val_accuracy"].append(val_metrics["accuracy"])
            history["val_auc"].append(val_metrics["auc"])
            
            # Log progress
            if (epoch + 1) % 10 == 0:
                logger.info(
                    f"Epoch {epoch + 1}/{epochs} | "
                    f"Train Loss: {train_loss:.4f} | "
                    f"Val Loss: {val_metrics['loss']:.4f} | "
                    f"Val Acc: {val_metrics['accuracy']:.4f} | "
                    f"Val AUC: {val_metrics['auc']:.4f}"
                )
            
            # Early stopping
            if val_metrics["loss"] < best_val_loss:
                best_val_loss = val_metrics["loss"]
                patience_counter = 0
                
                # Save checkpoint
                if checkpoint_dir:
                    self.save(checkpoint_dir / "best_model.pt")
            else:
                patience_counter += 1
                
            if patience_counter >= patience:
                logger.info(f"Early stopping at epoch {epoch + 1}")
                break
        
        # Final test evaluation
        test_metrics = self.evaluate(test_data)
        logger.info(
            f"Test Results | "
            f"Loss: {test_metrics['loss']:.4f} | "
            f"Accuracy: {test_metrics['accuracy']:.4f} | "
            f"AUC: {test_metrics['auc']:.4f}"
        )
        
        return history
    
    def predict_links(
        self,
        data: Data,
        source_nodes: Optional[List[int]] = None,
        top_k: int = 100,
    ) -> List[Tuple[int, int, float]]:
        """
        Predict top-k most likely links.
        
        Args:
             Graph data
            source_nodes: List of source node IDs to predict from (None = all)
            top_k: Number of top predictions to return
            
        Returns:
            List of (source_id, target_id, score) tuples
        """
        self.model.eval()
        
        with torch.no_grad():
            x = data.x.to(self.device)
            edge_index = data.edge_index.to(self.device)
            
            # Encode all nodes
            z = self.model.encode(x, edge_index)
            
            if source_nodes is None:
                source_nodes = list(range(data.num_nodes))
            
            predictions = []
            
            for source in source_nodes:
                # Get source embedding
                src_emb = z[source].unsqueeze(0)
                
                # Compute scores for all targets
                scores = (src_emb * z).sum(dim=1).sigmoid()
                
                # Get top-k targets
                top_scores, top_indices = torch.topk(scores, k=min(top_k, len(scores)))
                
                for target, score in zip(top_indices.cpu().numpy(), top_scores.cpu().numpy()):
                    if target != source:  # Exclude self-loops
                        predictions.append((source, int(target), float(score)))
            
            # Sort by score and return top-k
            predictions.sort(key=lambda x: x[2], reverse=True)
            return predictions[:top_k]
    
    def save(self, path: Path) -> None:
        """
        Save model checkpoint.
        
        Args:
            path: Path to save checkpoint
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "in_channels": self.in_channels,
            "hidden_channels": self.hidden_channels,
            "out_channels": self.out_channels,
        }, path)
        logger.info(f"Model saved to {path}")
    
    def load(self, path: Path) -> None:
        """
        Load model checkpoint.
        
        Args:
            path: Path to load checkpoint from
        """
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        logger.info(f"Model loaded from {path}")
