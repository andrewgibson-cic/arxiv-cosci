"""
Metrics collection and monitoring utilities.
Tracks API performance, database operations, and system health.
"""
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from packages.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Metric:
    """Single metric data point."""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class Counter:
    """Simple counter metric."""
    name: str
    count: int = 0
    tags: dict[str, str] = field(default_factory=dict)
    
    def increment(self, amount: int = 1) -> None:
        """Increment counter by amount."""
        self.count += amount
    
    def reset(self) -> int:
        """Reset counter and return previous value."""
        value = self.count
        self.count = 0
        return value


@dataclass
class Timer:
    """Timer for measuring duration of operations."""
    name: str
    start_time: float = field(default_factory=time.time)
    tags: dict[str, str] = field(default_factory=dict)
    
    def stop(self) -> float:
        """Stop timer and return duration in milliseconds."""
        duration_ms = (time.time() - self.start_time) * 1000
        logger.debug(
            "Timer stopped",
            metric=self.name,
            duration_ms=round(duration_ms, 2),
            **self.tags,
        )
        return duration_ms


class MetricsCollector:
    """
    Central metrics collector for the application.
    Tracks counters, timers, and gauges.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.counters: dict[str, Counter] = defaultdict(lambda: Counter(name="unknown"))
        self.timers: dict[str, list[float]] = defaultdict(list)
        self.gauges: dict[str, float] = {}
        self._start_time = time.time()
    
    def increment_counter(self, name: str, amount: int = 1, **tags: str) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Counter name
            amount: Amount to increment by
            **tags: Optional tags for the metric
        
        Example:
            >>> metrics.increment_counter("api.requests", path="/papers")
        """
        key = f"{name}:{':'.join(f'{k}={v}' for k, v in sorted(tags.items()))}"
        if key not in self.counters:
            self.counters[key] = Counter(name=name, tags=tags)
        self.counters[key].increment(amount)
    
    def record_timer(self, name: str, duration_ms: float, **tags: str) -> None:
        """
        Record a timer metric.
        
        Args:
            name: Timer name
            duration_ms: Duration in milliseconds
            **tags: Optional tags for the metric
        
        Example:
            >>> metrics.record_timer("db.query", 45.2, operation="read")
        """
        key = f"{name}:{':'.join(f'{k}={v}' for k, v in sorted(tags.items()))}"
        self.timers[key].append(duration_ms)
        
        # Log slow operations
        if duration_ms > 1000:
            logger.warning(
                "Slow operation detected",
                metric=name,
                duration_ms=round(duration_ms, 2),
                **tags,
            )
    
    def set_gauge(self, name: str, value: float, **tags: str) -> None:
        """
        Set a gauge metric (point-in-time value).
        
        Args:
            name: Gauge name
            value: Current value
            **tags: Optional tags for the metric
        
        Example:
            >>> metrics.set_gauge("db.connections", 5)
        """
        key = f"{name}:{':'.join(f'{k}={v}' for k, v in sorted(tags.items()))}"
        self.gauges[key] = value
    
    def get_timer_stats(self, name: str) -> dict[str, float]:
        """
        Get statistics for a timer metric.
        
        Args:
            name: Timer name
        
        Returns:
            Dictionary with min, max, avg, p50, p95, p99
        """
        values = []
        for key, durations in self.timers.items():
            if key.startswith(name):
                values.extend(durations)
        
        if not values:
            return {}
        
        values_sorted = sorted(values)
        n = len(values_sorted)
        
        return {
            "count": n,
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / n,
            "p50": values_sorted[int(n * 0.5)],
            "p95": values_sorted[int(n * 0.95)],
            "p99": values_sorted[int(n * 0.99)],
        }
    
    def get_summary(self) -> dict[str, Any]:
        """
        Get summary of all collected metrics.
        
        Returns:
            Dictionary with counters, timers, and gauges
        """
        uptime_seconds = time.time() - self._start_time
        
        # Summarize counters
        counter_summary = {
            name: counter.count
            for name, counter in self.counters.items()
        }
        
        # Summarize timers
        timer_summary = {}
        for name in set(key.split(":")[0] for key in self.timers.keys()):
            timer_summary[name] = self.get_timer_stats(name)
        
        return {
            "uptime_seconds": round(uptime_seconds, 2),
            "counters": counter_summary,
            "timers": timer_summary,
            "gauges": dict(self.gauges),
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.counters.clear()
        self.timers.clear()
        self.gauges.clear()
        self._start_time = time.time()
        logger.info("Metrics reset")


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.
    
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def timer_context(name: str, **tags: str):
    """
    Context manager for timing operations.
    
    Args:
        name: Timer name
        **tags: Optional tags for the metric
    
    Example:
        >>> with timer_context("api.request", method="GET"):
        ...     # Do work
        ...     pass
    """
    class TimerContext:
        def __init__(self, metric_name: str, metric_tags: dict[str, str]):
            self.name = metric_name
            self.tags = metric_tags
            self.start_time = 0.0
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            duration_ms = (time.time() - self.start_time) * 1000
            get_metrics_collector().record_timer(self.name, duration_ms, **self.tags)
    
    return TimerContext(name, tags)


# Convenience functions
def increment_counter(name: str, amount: int = 1, **tags: str) -> None:
    """Increment a counter metric (convenience function)."""
    get_metrics_collector().increment_counter(name, amount, **tags)


def record_timer(name: str, duration_ms: float, **tags: str) -> None:
    """Record a timer metric (convenience function)."""
    get_metrics_collector().record_timer(name, duration_ms, **tags)


def set_gauge(name: str, value: float, **tags: str) -> None:
    """Set a gauge metric (convenience function)."""
    get_metrics_collector().set_gauge(name, value, **tags)


def get_metrics_summary() -> dict[str, Any]:
    """Get summary of all metrics (convenience function)."""
    return get_metrics_collector().get_summary()