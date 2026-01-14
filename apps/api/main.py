"""
ArXiv Co-Scientist API Server
FastAPI backend for scientific paper exploration and ML predictions.
"""
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.routers import papers, search, graph, predictions, health, ingestion, system
from apps.api.dependencies import get_neo4j_client, get_chromadb_client
from packages.observability import (
    configure_logging,
    get_logger,
    RequestLoggingMiddleware,
    PerformanceMonitoringMiddleware,
    HealthCheckMiddleware,
)

# Configure structured logging
configure_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    json_logs=os.getenv("LOG_FORMAT", "console") == "json",
    development=os.getenv("ENVIRONMENT", "development") == "development",
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI app.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting ArXiv Co-Scientist API...")
    
    # Initialize database clients
    try:
        neo4j = await get_neo4j_client()
        await neo4j.verify_connection()
        logger.info("✓ Neo4j connection verified")
    except Exception as e:
        logger.error(f"✗ Neo4j connection failed: {e}")
    
    try:
        chroma = await get_chromadb_client()
        logger.info("✓ ChromaDB connection verified")
    except Exception as e:
        logger.error(f"✗ ChromaDB connection failed: {e}")
    
    logger.info("API server ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API server...")
    try:
        neo4j = await get_neo4j_client()
        await neo4j.close()
        logger.info("✓ Neo4j connection closed")
    except Exception:
        pass


# Create FastAPI app
app = FastAPI(
    title="ArXiv Co-Scientist API",
    description="Scientific Intelligence Engine for physics and mathematics research",
    version="0.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add observability middleware (order matters - applied in reverse)
app.add_middleware(HealthCheckMiddleware)  # Skip logging for health checks
app.add_middleware(RequestLoggingMiddleware)  # Log all requests
app.add_middleware(PerformanceMonitoringMiddleware, slow_request_threshold_ms=1000.0)  # Monitor performance

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # Alternative React port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(system.router, prefix="/api", tags=["System"])
app.include_router(papers.router, prefix="/api/papers", tags=["Papers"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(graph.router, prefix="/api/graph", tags=["Graph"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(ingestion.router, prefix="/api", tags=["Ingestion"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint - API information."""
    return {
        "name": "ArXiv Co-Scientist API",
        "version": "0.4.0",
        "docs": "/docs",
        "status": "operational",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if app.debug else "An unexpected error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn
    import socket
    
    def find_available_port(start_port: int = 8000, max_attempts: int = 10) -> int:
        """Find an available port starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            try:
                # Try to bind to the port
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("0.0.0.0", port))
                    logger.info(f"✓ Port {port} is available")
                    return port
            except OSError:
                logger.warning(f"✗ Port {port} is already in use, trying next...")
                continue
        
        # If no port found, raise error
        raise RuntimeError(f"Could not find available port in range {start_port}-{start_port + max_attempts}")
    
    # Find available port
    try:
        port = find_available_port(8000)
        logger.info(f"🚀 Starting server on port {port}")
        
        uvicorn.run(
            "apps.api.main:app",
            host="0.0.0.0",
            port=port,
            reload=True,
            log_level="info",
        )
    except RuntimeError as e:
        logger.error(f"Failed to start server: {e}")
        print(f"\n❌ Error: {e}")
        print("💡 Tip: Kill existing processes with: lsof -ti:8000 | xargs kill -9")
