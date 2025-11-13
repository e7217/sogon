"""
Job repository implementation with file-based persistence
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta

from .interfaces import JobRepository
from ..models.job import ProcessingJob, JobStatus

logger = logging.getLogger(__name__)


class FileBasedJobRepository(JobRepository):
    """
    File-based job repository with JSON persistence.

    Features:
    - Atomic writes with temp files
    - In-memory cache for performance
    - Automatic cleanup of old jobs
    - Thread-safe operations

    Storage structure:
        .sogon/
        └── jobs/
            ├── {job_id}.json
            └── ...
    """

    def __init__(self, storage_dir: Path = None):
        """
        Initialize repository.

        Args:
            storage_dir: Directory for job storage (default: .sogon/jobs)
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".sogon" / "jobs"

        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache for performance
        self._cache: dict = {}
        self._lock = asyncio.Lock()

        # Load existing jobs into cache
        self._load_cache()

        logger.info(f"Initialized FileBasedJobRepository at {self.storage_dir}")

    def _load_cache(self):
        """Load all existing jobs into memory cache."""
        try:
            for job_file in self.storage_dir.glob("*.json"):
                try:
                    with open(job_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        job = ProcessingJob.from_dict(data)
                        self._cache[job.id] = job
                except Exception as e:
                    logger.error(f"Failed to load job from {job_file}: {e}")

            logger.info(f"Loaded {len(self._cache)} jobs into cache")
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")

    def _get_job_file_path(self, job_id: str) -> Path:
        """Get file path for job."""
        return self.storage_dir / f"{job_id}.json"

    async def save_job(self, job: ProcessingJob) -> bool:
        """
        Save job with atomic write.

        Args:
            job: Job to save

        Returns:
            True if saved successfully
        """
        async with self._lock:
            try:
                # Update cache
                self._cache[job.id] = job

                # Write to file atomically
                job_file = self._get_job_file_path(job.id)
                temp_file = job_file.with_suffix(".tmp")

                # Write to temp file
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(job.to_dict(), f, indent=2, ensure_ascii=False)

                # Atomic rename
                temp_file.replace(job_file)

                logger.debug(f"Saved job {job.id} to {job_file}")
                return True

            except Exception as e:
                logger.error(f"Failed to save job {job.id}: {e}")
                return False

    async def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """
        Get job by ID (from cache).

        Args:
            job_id: Job identifier

        Returns:
            Job if found, None otherwise
        """
        async with self._lock:
            return self._cache.get(job_id)

    async def update_job_status(self, job_id: str, status: JobStatus) -> bool:
        """
        Update job status.

        Args:
            job_id: Job identifier
            status: New status

        Returns:
            True if updated successfully
        """
        job = await self.get_job(job_id)
        if job:
            job.status = status
            return await self.save_job(job)
        return False

    async def get_jobs_by_status(self, status: JobStatus) -> List[ProcessingJob]:
        """
        Get jobs by status.

        Args:
            status: Job status to filter by

        Returns:
            List of jobs with matching status
        """
        async with self._lock:
            return [job for job in self._cache.values() if job.status == status]

    async def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ProcessingJob]:
        """
        List jobs with filtering and pagination.

        Args:
            status: Optional status filter
            limit: Maximum jobs to return
            offset: Number of jobs to skip

        Returns:
            List of jobs
        """
        async with self._lock:
            jobs = list(self._cache.values())

            # Filter by status
            if status:
                jobs = [j for j in jobs if j.status == status]

            # Sort by created_at descending
            jobs.sort(key=lambda j: j.created_at, reverse=True)

            # Paginate
            return jobs[offset:offset + limit]

    async def delete_job(self, job_id: str) -> bool:
        """
        Delete job from cache and filesystem.

        Args:
            job_id: Job identifier

        Returns:
            True if deleted successfully
        """
        async with self._lock:
            try:
                # Remove from cache
                if job_id in self._cache:
                    del self._cache[job_id]

                # Remove file
                job_file = self._get_job_file_path(job_id)
                if job_file.exists():
                    job_file.unlink()

                logger.info(f"Deleted job {job_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to delete job {job_id}: {e}")
                return False

    async def cleanup_old_jobs(self, days: int = 7) -> int:
        """
        Clean up old completed/failed jobs.

        Args:
            days: Delete jobs older than this many days

        Returns:
            Number of jobs deleted
        """
        async with self._lock:
            try:
                cutoff = datetime.now() - timedelta(days=days)
                deleted_count = 0

                # Find jobs to delete
                jobs_to_delete = []
                for job in self._cache.values():
                    # Delete completed/failed jobs older than cutoff
                    if job.status.is_terminal and job.completed_at:
                        if job.completed_at < cutoff:
                            jobs_to_delete.append(job.id)

                # Delete jobs
                for job_id in jobs_to_delete:
                    await self.delete_job(job_id)
                    deleted_count += 1

                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old jobs (>{days} days)")

                return deleted_count

            except Exception as e:
                logger.error(f"Failed to cleanup old jobs: {e}")
                return 0

    async def get_stats(self) -> dict:
        """
        Get repository statistics.

        Returns:
            Dictionary with statistics
        """
        async with self._lock:
            status_counts = {}
            for job in self._cache.values():
                status = job.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

            return {
                "total_jobs": len(self._cache),
                "status_counts": status_counts,
                "storage_dir": str(self.storage_dir),
                "disk_files": len(list(self.storage_dir.glob("*.json")))
            }


# Legacy in-memory implementation (for backward compatibility)
class JobRepositoryImpl(JobRepository):
    """In-memory job repository (legacy)"""

    def __init__(self):
        self._jobs = {}

    async def save_job(self, job: ProcessingJob) -> bool:
        """Save processing job"""
        self._jobs[job.id] = job
        return True

    async def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Get processing job by ID"""
        return self._jobs.get(job_id)

    async def update_job_status(self, job_id: str, status: JobStatus) -> bool:
        """Update job status"""
        if job_id in self._jobs:
            self._jobs[job_id].status = status
            return True
        return False

    async def get_jobs_by_status(self, status: JobStatus) -> List[ProcessingJob]:
        """Get jobs by status"""
        return [job for job in self._jobs.values() if job.status == status]

    async def delete_job(self, job_id: str) -> bool:
        """Delete job"""
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False

    async def cleanup_old_jobs(self, days: int = 7) -> int:
        """Clean up jobs older than specified days"""
        return 0