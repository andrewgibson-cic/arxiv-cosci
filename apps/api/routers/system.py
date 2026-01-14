"""
System Router - Health checks and system management
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import subprocess
import os
from pathlib import Path
import psutil

router = APIRouter(prefix="/system", tags=["system"])


class ServiceStatus(BaseModel):
    """Status of a service"""
    name: str
    status: str  # "running", "stopped", "error", "unknown"
    details: Optional[str] = None


class SystemHealth(BaseModel):
    """Overall system health"""
    status: str  # "healthy", "degraded", "unhealthy"
    services: list[ServiceStatus]
    prerequisites: Dict[str, bool]
    errors: list[str] = []


class PrerequisiteCheck(BaseModel):
    """Prerequisite check results"""
    docker: bool
    docker_running: bool
    poetry: bool
    node: bool
    python: bool
    api_key_configured: bool
    errors: list[str] = []


@router.get("/health", response_model=SystemHealth)
async def check_system_health():
    """
    Comprehensive system health check
    """
    services = []
    errors = []
    
    # Check Docker services
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Check Neo4j
            neo4j_running = "neo4j" in result.stdout and "running" in result.stdout.lower()
            services.append(ServiceStatus(
                name="neo4j",
                status="running" if neo4j_running else "stopped",
                details="Graph database"
            ))
            
            # Check Grobid
            grobid_running = "grobid" in result.stdout and "running" in result.stdout.lower()
            services.append(ServiceStatus(
                name="grobid",
                status="running" if grobid_running else "stopped",
                details="PDF parser"
            ))
        else:
            services.append(ServiceStatus(
                name="docker",
                status="error",
                details="Docker Compose not responding"
            ))
            errors.append("Docker Compose not available")
    except Exception as e:
        services.append(ServiceStatus(
            name="docker",
            status="error",
            details=str(e)
        ))
        errors.append(f"Docker check failed: {e}")
    
    # Check Neo4j connectivity
    try:
        from packages.knowledge.neo4j_client import Neo4jClient
        neo4j = Neo4jClient()
        if await neo4j.health_check():
            services.append(ServiceStatus(
                name="neo4j_connection",
                status="running",
                details="Database connected"
            ))
        else:
            services.append(ServiceStatus(
                name="neo4j_connection",
                status="error",
                details="Cannot connect to database"
            ))
            errors.append("Neo4j connection failed")
    except Exception as e:
        services.append(ServiceStatus(
            name="neo4j_connection",
            status="error",
            details=str(e)
        ))
        errors.append(f"Neo4j check failed: {e}")
    
    # Check LLM availability
    try:
        from packages.ai.factory import get_llm_client
        llm = get_llm_client()
        if await llm.is_available():
            services.append(ServiceStatus(
                name="llm",
                status="running",
                details=f"Provider: {os.getenv('LLM_PROVIDER', 'gemini')}"
            ))
        else:
            services.append(ServiceStatus(
                name="llm",
                status="error",
                details="LLM not available"
            ))
            errors.append("LLM check failed")
    except Exception as e:
        services.append(ServiceStatus(
            name="llm",
            status="error",
            details=str(e)
        ))
        errors.append(f"LLM check failed: {e}")
    
    # Determine overall status
    running_services = sum(1 for s in services if s.status == "running")
    total_services = len(services)
    
    if running_services == total_services:
        overall_status = "healthy"
    elif running_services > 0:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return SystemHealth(
        status=overall_status,
        services=services,
        prerequisites={
            "docker": True,  # If we got here, basic checks passed
            "python": True,
            "api_keys": bool(os.getenv("GEMINI_API_KEY"))
        },
        errors=errors
    )


@router.get("/prerequisites", response_model=PrerequisiteCheck)
async def check_prerequisites():
    """
    Check if all prerequisites are installed and configured
    """
    errors = []
    
    # Check Docker
    docker_installed = False
    docker_running = False
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, timeout=5)
        docker_installed = result.returncode == 0
        
        if docker_installed:
            result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            docker_running = result.returncode == 0
    except Exception as e:
        errors.append(f"Docker check failed: {e}")
    
    # Check Poetry
    poetry_installed = False
    try:
        result = subprocess.run(["poetry", "--version"], capture_output=True, timeout=5)
        poetry_installed = result.returncode == 0
    except Exception as e:
        errors.append(f"Poetry check failed: {e}")
    
    # Check Node
    node_installed = False
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, timeout=5)
        node_installed = result.returncode == 0
    except Exception as e:
        errors.append(f"Node check failed: {e}")
    
    # Check Python
    python_installed = True  # If we're running, Python is installed
    
    # Check API key
    api_key_configured = bool(os.getenv("GEMINI_API_KEY"))
    if not api_key_configured:
        errors.append("GEMINI_API_KEY not configured in .env file")
    
    return PrerequisiteCheck(
        docker=docker_installed,
        docker_running=docker_running,
        poetry=poetry_installed,
        node=node_installed,
        python=python_installed,
        api_key_configured=api_key_configured,
        errors=errors
    )


@router.post("/init")
async def initialize_system():
    """
    Initialize the system (create directories, setup database schema, etc.)
    """
    try:
        # Create necessary directories
        directories = [
            "data/batch_collection",
            "data/processed",
            "data/chroma",
            "logs"
        ]
        
        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize Neo4j schema
        try:
            from packages.knowledge.neo4j_client import Neo4jClient
            neo4j = Neo4jClient()
            await neo4j.initialize_schema()
        except Exception as e:
            return {
                "status": "partial",
                "message": f"Directories created but Neo4j init failed: {e}",
                "directories_created": directories
            }
        
        return {
            "status": "success",
            "message": "System initialized successfully",
            "directories_created": directories
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")


@router.get("/stats")
async def get_system_stats():
    """
    Get system resource usage statistics
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "percent": disk.percent
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")