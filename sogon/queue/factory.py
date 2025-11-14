"""Factory for creating job queue instances based on configuration."""

import logging
from typing import Literal

from .interface import JobQueue
from .memory_queue import MemoryJobQueue

logger = logging.getLogger(__name__)

QueueBackend = Literal["memory", "redis", "celery"]


def create_queue(
    backend: QueueBackend = "memory",
    max_size: int = 150,
    **kwargs
) -> JobQueue:
    """
    Create a job queue instance based on configuration.

    Args:
        backend: Queue backend type ("memory", "redis", "celery")
        max_size: Maximum queue capacity
        **kwargs: Backend-specific configuration options

    Returns:
        JobQueue instance

    Examples:
        >>> # In-memory queue (default)
        >>> queue = create_queue("memory", max_size=150)

        >>> # Redis queue (future)
        >>> queue = create_queue("redis", redis_url="redis://localhost:6379/0")

        >>> # Celery queue (future)
        >>> queue = create_queue("celery", broker_url="redis://localhost:6379/1")

    Migration path:
        Current: memory (asyncio.Queue)
        Future: redis (when > 1,000 jobs/day or multi-instance needed)
        Future: celery (when complex workflows with chaining/retries needed)
    """
    if backend == "memory":
        logger.info(f"Creating MemoryJobQueue with max_size={max_size}")
        return MemoryJobQueue(max_size=max_size)

    elif backend == "redis":
        # Future implementation
        raise NotImplementedError(
            "Redis queue backend not yet implemented. "
            "Use 'memory' backend for now. "
            "Migration guide: See docs/queue_migration_guide.md"
        )

    elif backend == "celery":
        # Future implementation
        raise NotImplementedError(
            "Celery queue backend not yet implemented. "
            "Use 'memory' backend for now. "
            "Migration guide: See docs/queue_migration_guide.md"
        )

    else:
        raise ValueError(
            f"Unknown queue backend: {backend}. "
            f"Supported backends: memory, redis, celery"
        )


def validate_queue_config(backend: QueueBackend, **kwargs) -> bool:
    """
    Validate queue configuration before creation.

    Args:
        backend: Queue backend type
        **kwargs: Backend-specific configuration

    Returns:
        True if configuration is valid

    Raises:
        ValueError: If configuration is invalid
    """
    if backend == "memory":
        max_size = kwargs.get("max_size", 150)
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        if max_size > 10000:
            logger.warning(
                f"Large max_size={max_size} may consume significant memory. "
                f"Consider Redis backend for > 1,000 jobs/day."
            )

    elif backend == "redis":
        redis_url = kwargs.get("redis_url")
        if not redis_url:
            raise ValueError("redis_url required for Redis backend")

    elif backend == "celery":
        broker_url = kwargs.get("broker_url")
        if not broker_url:
            raise ValueError("broker_url required for Celery backend")

    return True
