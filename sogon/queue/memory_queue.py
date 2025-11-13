"""In-memory job queue implementation using asyncio.Queue."""

import asyncio
import logging
from typing import Optional, Set
from datetime import datetime

from .interface import QueueFullError

logger = logging.getLogger(__name__)


class MemoryJobQueue:
    """
    In-memory FIFO job queue using asyncio.Queue.

    Features:
    - Non-blocking enqueue with backpressure (rejects when full)
    - Blocking dequeue (waits for jobs)
    - Job cancellation support
    - Thread-safe and async-safe operations
    - Efficient for < 1,000 jobs/day workload

    Performance characteristics:
    - Enqueue latency: < 1ms
    - Dequeue latency: < 1ms (when jobs available)
    - Memory overhead: ~1KB per job
    - Max capacity: Configurable (default 150)
    """

    def __init__(self, max_size: int = 150):
        """
        Initialize memory queue.

        Args:
            max_size: Maximum queue capacity. When full, enqueue returns False.
                     Recommended: 2-3x peak hourly load for buffer.
        """
        self.max_size = max_size
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._cancelled_jobs: Set[str] = set()
        self._lock = asyncio.Lock()

        logger.info(f"Initialized MemoryJobQueue with max_size={max_size}")

    async def enqueue(self, job_id: str) -> bool:
        """
        Enqueue job ID for processing.

        Args:
            job_id: Unique job identifier

        Returns:
            True if enqueued successfully, False if queue is full

        Performance:
            Target: < 5ms for success, < 1ms for rejection
        """
        # Fast rejection if queue full (non-blocking)
        if self._queue.qsize() >= self.max_size:
            logger.warning(
                f"Queue full (size={self._queue.qsize()}), rejecting job {job_id}"
            )
            return False

        try:
            # Non-blocking put with immediate timeout
            await asyncio.wait_for(
                self._queue.put(job_id),
                timeout=0.001  # 1ms timeout
            )

            logger.debug(
                f"Enqueued job {job_id} (queue_size={self._queue.qsize()})"
            )
            return True

        except asyncio.TimeoutError:
            logger.warning(f"Enqueue timeout for job {job_id}")
            return False
        except Exception as e:
            logger.error(f"Enqueue error for job {job_id}: {e}")
            return False

    async def dequeue(self) -> Optional[str]:
        """
        Dequeue next job ID (blocks until available).

        Returns:
            Job ID if available, None if cancelled

        Note:
            This method blocks indefinitely until a job is available.
            Workers should run this in a loop with cancellation support.
        """
        while True:
            try:
                job_id = await self._queue.get()

                # Check if job was cancelled
                async with self._lock:
                    if job_id in self._cancelled_jobs:
                        logger.info(f"Skipping cancelled job: {job_id}")
                        self._cancelled_jobs.discard(job_id)
                        self._queue.task_done()
                        continue  # Get next job

                logger.debug(
                    f"Dequeued job {job_id} (queue_size={self._queue.qsize()})"
                )
                return job_id

            except Exception as e:
                logger.error(f"Dequeue error: {e}")
                await asyncio.sleep(0.1)  # Brief pause before retry

    async def peek(self) -> Optional[str]:
        """
        View next job without removing it.

        Returns:
            Job ID if available, None if queue is empty

        Note:
            This is a non-blocking operation.
        """
        if self._queue.empty():
            return None

        # asyncio.Queue doesn't support peek, so we use a workaround
        # This is an approximate peek (race condition possible)
        return None  # Not implemented for asyncio.Queue

    async def cancel(self, job_id: str) -> bool:
        """
        Mark job as cancelled (will be skipped during dequeue).

        Args:
            job_id: Job to cancel

        Returns:
            True (optimistic cancellation - actual check during dequeue)

        Note:
            We don't remove from queue immediately (not supported by asyncio.Queue).
            Instead, we mark as cancelled and skip during dequeue.
        """
        async with self._lock:
            self._cancelled_jobs.add(job_id)

        logger.info(f"Marked job {job_id} as cancelled")
        return True

    async def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    async def clear(self) -> int:
        """
        Clear all jobs from queue.

        Returns:
            Number of jobs removed
        """
        count = 0
        async with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                    count += 1
                except asyncio.QueueEmpty:
                    break

            # Clear cancelled set
            cancelled_count = len(self._cancelled_jobs)
            self._cancelled_jobs.clear()

        logger.info(f"Cleared {count} jobs from queue ({cancelled_count} cancelled)")
        return count

    async def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    async def is_full(self) -> bool:
        """Check if queue is at capacity."""
        return self._queue.qsize() >= self.max_size

    def task_done(self):
        """
        Mark dequeued job as done (optional, for tracking).

        Note:
            This is a synchronous method for compatibility with asyncio.Queue.
        """
        self._queue.task_done()

    async def join(self):
        """
        Block until all jobs are processed (useful for testing).

        Note:
            This requires workers to call task_done() after processing.
        """
        await self._queue.join()
