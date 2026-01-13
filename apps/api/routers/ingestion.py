"""
Ingestion Router - Manage paper collection and processing
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import json
import subprocess
from pathlib import Path
from datetime import datetime

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

# Global state for tracking ingestion progress
ingestion_state = {
    "is_running": False,
    "current_batch": 0,
    "total_batches": 0,
    "papers_processed": 0,
    "papers_failed": 0,
    "started_at": None,
    "estimated_completion": None,
    "current_status": "idle",
    "error": None,
}


class IngestionConfig(BaseModel):
    """Configuration for paper ingestion"""
    num_papers: int = 100
    batch_size: int = 10
    use_semantic_scholar: bool = True
    use_arxiv: bool = True
    process_pdfs: bool = True


class IngestionStats(BaseModel):
    """Statistics about paper collection"""
    total_papers: int
    processed_papers: int
    unprocessed_papers: int
    total_size_mb: float
    categories: Dict[str, int]
    last_updated: Optional[str]


@router.get("/stats", response_model=IngestionStats)
async def get_ingestion_stats():
    """
    Get statistics about the current paper collection
    """
    try:
        data_dir = Path("data")
        
        # Count papers in JSON files
        total_papers = 0
        categories = {}
        total_size = 0
        
        for json_file in data_dir.glob("**/*.json"):
            if "chroma" in str(json_file):
                continue
                
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    
                # Handle different JSON structures
                papers = data if isinstance(data, list) else data.get("papers", [])
                total_papers += len(papers)
                
                # Count categories
                for paper in papers:
                    category = paper.get("category", "Unknown")
                    categories[category] = categories.get(category, 0) + 1
                
                # Get file size
                total_size += json_file.stat().st_size
                
            except Exception as e:
                print(f"Error reading {json_file}: {e}")
                continue
        
        # Check for processed papers in Neo4j or vector DB
        # TODO: Query actual databases when available
        processed_papers = 0  # Placeholder
        
        return IngestionStats(
            total_papers=total_papers,
            processed_papers=processed_papers,
            unprocessed_papers=total_papers - processed_papers,
            total_size_mb=round(total_size / (1024 * 1024), 2),
            categories=categories,
            last_updated=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/status")
async def get_ingestion_status():
    """
    Get the current status of any running ingestion process
    """
    return {
        **ingestion_state,
        "progress_percentage": (
            (ingestion_state["papers_processed"] / 
             (ingestion_state["total_batches"] * 10)) * 100
            if ingestion_state["total_batches"] > 0 else 0
        )
    }


async def run_ingestion_process(config: IngestionConfig):
    """
    Background task to run the paper ingestion process
    """
    global ingestion_state
    
    try:
        ingestion_state["is_running"] = True
        ingestion_state["started_at"] = datetime.now().isoformat()
        ingestion_state["current_status"] = "initializing"
        ingestion_state["total_batches"] = config.num_papers // config.batch_size
        ingestion_state["error"] = None
        
        # Run the batch collection script
        script_path = Path("scripts/batch_collect_and_process.py")
        
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        ingestion_state["current_status"] = "collecting papers"
        
        # Execute the script with progress tracking
        # Note: This is a simplified version - in production you'd want
        # to stream output and parse progress
        process = subprocess.Popen(
            ["python3", str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Simulate progress updates (in reality, parse script output)
        for i in range(ingestion_state["total_batches"]):
            await asyncio.sleep(5)  # Simulated delay
            ingestion_state["current_batch"] = i + 1
            ingestion_state["papers_processed"] = (i + 1) * config.batch_size
            ingestion_state["current_status"] = f"Processing batch {i + 1}/{ingestion_state['total_batches']}"
        
        # Wait for process to complete
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            ingestion_state["current_status"] = "completed"
        else:
            ingestion_state["current_status"] = "failed"
            ingestion_state["error"] = stderr
            
    except Exception as e:
        ingestion_state["current_status"] = "failed"
        ingestion_state["error"] = str(e)
        
    finally:
        ingestion_state["is_running"] = False


@router.post("/start")
async def start_ingestion(
    config: IngestionConfig,
    background_tasks: BackgroundTasks
):
    """
    Start the paper ingestion process
    """
    global ingestion_state
    
    if ingestion_state["is_running"]:
        raise HTTPException(
            status_code=409,
            detail="Ingestion process already running"
        )
    
    # Reset state
    ingestion_state["papers_processed"] = 0
    ingestion_state["papers_failed"] = 0
    ingestion_state["current_batch"] = 0
    
    # Start background task
    background_tasks.add_task(run_ingestion_process, config)
    
    return {
        "message": "Ingestion process started",
        "config": config.dict()
    }


@router.post("/stop")
async def stop_ingestion():
    """
    Stop the running ingestion process
    """
    global ingestion_state
    
    if not ingestion_state["is_running"]:
        raise HTTPException(
            status_code=400,
            detail="No ingestion process is running"
        )
    
    # TODO: Implement graceful shutdown
    ingestion_state["current_status"] = "stopping"
    
    return {"message": "Ingestion process stopping"}


@router.delete("/clear")
async def clear_data():
    """
    Clear all collected paper data (USE WITH CAUTION)
    """
    try:
        data_dir = Path("data")
        
        # Count files before deletion
        files_deleted = 0
        for json_file in data_dir.glob("**/*.json"):
            if "chroma" not in str(json_file) and json_file.name not in ["sample_papers.json"]:
                json_file.unlink()
                files_deleted += 1
        
        return {
            "message": f"Deleted {files_deleted} data files",
            "files_deleted": files_deleted
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear  {str(e)}")