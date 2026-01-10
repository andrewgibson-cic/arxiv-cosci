"""
FastAPI middleware for request/response logging and monitoring.
"""
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from packages.observability.logging import get_logger, bind_context, clear_context

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all HTTP requests and responses.
    Adds request ID tracking and timing information.
    """
    
    def __init__(self, app: ASGIApp):
        """Initialize middleware."""
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler
        
        Returns:
            HTTP response
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Bind request context for all logs during this request
        bind_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )
        
        # Start timing
        start_time = time.time()
        
        # Log request start
        logger.info(
            "Request started",
            query_params=dict(request.query_params),
            headers={k: v for k, v in request.headers.items() if k.lower() not in ["authorization", "cookie"]},
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            logger.info(
                "Request completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            logger.error(
                "Request failed",
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )
            raise
        
        finally:
            # Clear request context
            clear_context()


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for monitoring API performance.
    Logs slow requests and tracks response times.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        slow_request_threshold_ms: float = 1000.0,
    ):
        """
        Initialize middleware.
        
        Args:
            app: ASGI application
            slow_request_threshold_ms: Threshold in ms for slow request warnings
        """
        super().__init__(app)
        self.slow_threshold = slow_request_threshold_ms
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Monitor request performance.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler
        
        Returns:
            HTTP response
        """
        start_time = time.time()
        
        response = await call_next(request)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Add performance header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        
        # Warn on slow requests
        if duration_ms > self.slow_threshold:
            logger.warning(
                "Slow request detected",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                threshold_ms=self.slow_threshold,
            )
        
        return response


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """
    Middleware to skip logging for health check endpoints.
    Reduces log noise from monitoring systems.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        health_check_paths: list[str] | None = None,
    ):
        """
        Initialize middleware.
        
        Args:
            app: ASGI application
            health_check_paths: List of paths to skip logging (default: ["/health", "/api/health"])
        """
        super().__init__(app)
        self.health_check_paths = health_check_paths or ["/health", "/api/health", "/api/health/ready"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Skip logging for health check endpoints.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler
        
        Returns:
            HTTP response
        """
        # Skip logging for health checks
        if request.url.path in self.health_check_paths:
            return await call_next(request)
        
        # Process normally for other requests
        return await call_next(request)