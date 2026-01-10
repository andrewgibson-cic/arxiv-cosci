"""
Predictions Router
Endpoints for ML predictions and hypothesis generation.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from apps.api.dependencies import get_neo4j_client
from packages.knowledge.neo4j_client import Neo4jClient


router = APIRouter()


class LinkPrediction(BaseModel):
    """Predicted citation link."""
    source: str = Field(..., description="Source paper arXiv ID")
    target: str = Field(..., description="Target paper arXiv ID")
    score: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence")
    reason: str = Field(..., description="Explanation for prediction")


class LinkPredictionsResponse(BaseModel):
    """Response with predicted links."""
    predictions: list[LinkPrediction]
    total: int


class Hypothesis(BaseModel):
    """Research hypothesis."""
    id: str
    title: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    papers: list[str] = Field(..., description="Related paper IDs")
    gap_type: str


class HypothesesResponse(BaseModel):
    """Response with generated hypotheses."""
    hypotheses: list[Hypothesis]
    total: int


@router.get("/links", response_model=LinkPredictionsResponse)
async def get_link_predictions(
    limit: int = Query(10, ge=1, le=50, description="Maximum predictions"),
    neo4j: Neo4jClient = Depends(get_neo4j_client),
) -> LinkPredictionsResponse:
    """
    Get predicted citation links from GraphSAGE model.
    Returns papers that should likely cite each other.
    """
    try:
        # Query predicted citations from Neo4j
        query = """
        MATCH (source:Paper)-[r:PREDICTED_CITATION]->(target:Paper)
        RETURN source.arxiv_id as source, 
               target.arxiv_id as target,
               r.score as score,
               r.reason as reason
        ORDER BY r.score DESC
        LIMIT $limit
        """
        
        records = await neo4j.execute_query(query, {"limit": limit})
        
        predictions = []
        for record in records:
            predictions.append(
                LinkPrediction(
                    source=record.get("source", ""),
                    target=record.get("target", ""),
                    score=record.get("score", 0.0),
                    reason=record.get("reason", "Structural similarity"),
                )
            )
        
        return LinkPredictionsResponse(
            predictions=predictions,
            total=len(predictions),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.get("/hypotheses", response_model=HypothesesResponse)
async def get_hypotheses(
    limit: int = Query(10, ge=1, le=50, description="Maximum hypotheses"),
    neo4j: Neo4jClient = Depends(get_neo4j_client),
) -> HypothesesResponse:
    """
    Get generated research hypotheses from structural holes analysis.
    Returns promising research directions based on knowledge graph gaps.
    """
    try:
        # Query hypotheses from Neo4j
        query = """
        MATCH (h:Hypothesis)
        RETURN h.id as id,
               h.title as title, 
               h.description as description,
               h.confidence as confidence,
               h.papers as papers,
               h.gap_type as gap_type
        ORDER BY h.confidence DESC
        LIMIT $limit
        """
        
        records = await neo4j.execute_query(query, {"limit": limit})
        
        hypotheses = []
        for record in records:
            hypotheses.append(
                Hypothesis(
                    id=record.get("id", ""),
                    title=record.get("title", ""),
                    description=record.get("description", ""),
                    confidence=record.get("confidence", 0.0),
                    papers=record.get("papers", []),
                    gap_type=record.get("gap_type", "unknown"),
                )
            )
        
        return HypothesesResponse(
            hypotheses=hypotheses,
            total=len(hypotheses),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hypothesis error: {str(e)}")