"""Abstract interface for job queue implementations."""

from typing import Protocol, Optional


class JobQueue(Protocol):
    """
    Abstract job queue interface for async job processing.

    This protocol defines the contract that all queue implementations
    (in-memory, Redis, Celery) must follow for easy swapping.
    """

    async def enqueue(self, job_id: str) -> bool:
        """
        Add a job to the queue.

        Args:
            job_id: Unique job identifier

        Returns:
            True if enqueued successfully, False if queue is full or error occurred

        Raises:
            QueueFullError: When queue capacity is exceeded (optional)
        """
        ...

    async def dequeue(self) -> Optional[str]:
        """
        Remove and return the next job ID from the queue.

        Returns:
            Job ID if available, None if queue is empty

        Note:
            This operation should block until a job is available or timeout occurs.
        """
        ...

    async def peek(self) -> Optional[str]:
        """
        View the next job ID without removing it from the queue.

        Returns:
            Job ID if available, None if queue is empty
        """
        ...

    async def cancel(self, job_id: str) -> bool:
        """
        Cancel a queued job (mark for skipping).

        Args:
            job_id: Job identifier to cancel

        Returns:
            True if job was found and cancelled, False otherwise

        Note:
            Cancelled jobs will be skipped by workers during dequeue.
        """
        ...

    async def size(self) -> int:
        """
        Get the current number of jobs in the queue.

        Returns:
            Number of pending jobs
        """
        ...

    async def clear(self) -> int:
        """
        Remove all jobs from the queue.

        Returns:
            Number of jobs removed

        Warning:
            This operation should be used carefully, typically only for testing
            or emergency maintenance.
        """
        ...

    async def is_empty(self) -> bool:
        """
        Check if the queue is empty.

        Returns:
            True if queue has no jobs, False otherwise
        """
        ...

    async def is_full(self) -> bool:
        """
        Check if the queue is at capacity.

        Returns:
            True if queue cannot accept more jobs, False otherwise
        """
        ...


class QueueFullError(Exception):
    """Raised when attempting to enqueue to a full queue."""
    pass


class QueueEmptyError(Exception):
    """Raised when attempting to dequeue from an empty queue with no wait."""
    pass
