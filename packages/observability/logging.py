"""
Structured logging configuration using structlog.
Provides production-ready logging with JSON output, request tracking, and context.
"""
import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries."""
    event_dict["app"] = "arxiv-cosci"
    event_dict["version"] = "0.4.0"
    return event_dict


def censor_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Remove sensitive data from logs."""
    sensitive_keys = ["password", "api_key", "token", "secret"]
    
    for key in list(event_dict.keys()):
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            event_dict[key] = "***REDACTED***"
    
    return event_dict


def configure_logging(
    level: str = "INFO",
    json_logs: bool = False,
    development: bool = False,
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, output logs in JSON format (production)
        development: If True, use colorful console output (development)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Shared processors for all configurations
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
        censor_sensitive_data,
    ]
    
    if development:
        # Development: Colorful console output
        processors: list[Processor] = shared_processors + [
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    elif json_logs:
        # Production: JSON logs for structured logging systems
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Default: Human-readable but structured
        processors = shared_processors + [
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.dev.ConsoleRenderer(colors=False),
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__ of the module)
    
    Returns:
        Configured structlog logger
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing paper", arxiv_id="2401.12345", status="success")
    """
    return structlog.get_logger(name)


# Context managers for adding context to logs
class LogContext:
    """Context manager for adding temporary context to logs."""
    
    def __init__(self, **kwargs: Any):
        """
        Initialize log context.
        
        Args:
            **kwargs: Key-value pairs to add to log context
        
        Example:
            >>> with LogContext(request_id="abc123", user_id="user1"):
            ...     logger.info("Processing request")
        """
        self.context = kwargs
        self.token = None
    
    def __enter__(self) -> "LogContext":
        """Enter context and bind variables."""
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and unbind variables."""
        structlog.contextvars.unbind_contextvars(*self.context.keys())


def bind_context(**kwargs: Any) -> None:
    """
    Bind context variables that will be included in all subsequent logs.
    
    Args:
        **kwargs: Key-value pairs to bind to context
    
    Example:
        >>> bind_context(request_id="abc123")
        >>> logger.info("Request started")  # Will include request_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """
    Unbind context variables.
    
    Args:
        *keys: Keys to unbind from context
    
    Example:
        >>> unbind_context("request_id")
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """Clear all context variables."""
    structlog.contextvars.clear_contextvars()