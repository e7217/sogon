"""Background worker for processing transcription jobs from queue."""

import asyncio
import logging
import signal
from typing import Optional
from datetime import datetime

from ..queue.interface import JobQueue
from ..repositories.interfaces import JobRepository
from ..models.job import JobStatus, ProcessingJob
from ..services.workflow_service import WorkflowServiceImpl

logger = logging.getLogger(__name__)


class JobWorker:
    """
    Background worker for processing transcription jobs.

    Features:
    - Concurrent job processing with semaphore control
    - Exponential backoff retry (1s, 2s, 4s delays)
    - Graceful shutdown on SIGTERM/SIGINT
    - Job cancellation support
    - Progress tracking and status updates
    """

    def __init__(
        self,
        queue: JobQueue,
        job_repository: JobRepository,
        workflow_service: WorkflowServiceImpl,
        max_concurrent_jobs: int = 6,
        worker_id: str = "worker-1"
    ):
        """
        Initialize worker.

        Args:
            queue: Job queue for dequeuing jobs
            job_repository: Repository for job persistence
            workflow_service: Service for executing transcription workflows
            max_concurrent_jobs: Maximum concurrent jobs (GPU/CPU limit)
            worker_id: Unique worker identifier for logging
        """
        self.queue = queue
        self.job_repository = job_repository
        self.workflow_service = workflow_service
        self.max_concurrent_jobs = max_concurrent_jobs
        self.worker_id = worker_id

        self._running = False
        self._tasks: set = set()
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._shutdown_event = asyncio.Event()

        logger.info(
            f"Initialized {worker_id} with max_concurrent_jobs={max_concurrent_jobs}"
        )

    async def start(self):
        """
        Start worker processing loop.

        This method runs indefinitely until shutdown is triggered via SIGTERM/SIGINT
        or explicitly by calling stop().
        """
        self._running = True
        logger.info(f"{self.worker_id} starting...")

        # Register signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self.stop())
            )

        try:
            while self._running:
                try:
                    # Check if we can accept more jobs
                    if len(self._tasks) < self.max_concurrent_jobs:
                        # Dequeue next job (blocks until available)
                        job_id = await asyncio.wait_for(
                            self.queue.dequeue(),
                            timeout=1.0  # 1 second timeout to check shutdown
                        )

                        if job_id:
                            logger.info(f"{self.worker_id} dequeued job: {job_id}")

                            # Create processing task
                            task = asyncio.create_task(
                                self._process_job_with_concurrency(job_id)
                            )
                            self._tasks.add(task)
                            task.add_done_callback(self._tasks.discard)
                    else:
                        # At capacity, brief wait
                        await asyncio.sleep(0.5)

                except asyncio.TimeoutError:
                    # No jobs available, check shutdown
                    if self._shutdown_event.is_set():
                        break
                    continue

                except Exception as e:
                    logger.error(f"{self.worker_id} error in main loop: {e}")
                    await asyncio.sleep(1)

        finally:
            logger.info(f"{self.worker_id} stopping...")

            # Wait for all tasks to complete
            if self._tasks:
                logger.info(
                    f"{self.worker_id} waiting for {len(self._tasks)} active jobs to complete"
                )
                await asyncio.gather(*self._tasks, return_exceptions=True)

            logger.info(f"{self.worker_id} stopped")

    async def stop(self):
        """
        Stop worker gracefully.

        Sets shutdown flag and waits for current jobs to complete.
        """
        if not self._running:
            return

        logger.info(f"{self.worker_id} received shutdown signal")
        self._running = False
        self._shutdown_event.set()

    async def _process_job_with_concurrency(self, job_id: str):
        """
        Process job with semaphore-based concurrency control.

        Args:
            job_id: Job identifier to process
        """
        async with self._semaphore:
            await self._process_job(job_id)

    async def _process_job(self, job_id: str):
        """
        Process a single job with retry logic.

        Args:
            job_id: Job identifier to process
        """
        try:
            # Get job from repository
            job = await self.job_repository.get_job(job_id)
            if not job:
                logger.error(f"Job not found in repository: {job_id}")
                return

            # Check if job was cancelled
            if job.status == JobStatus.CANCELLED:
                logger.info(f"Skipping cancelled job: {job_id}")
                return

            # Mark job as dequeued
            job.mark_dequeued()
            await self.job_repository.save_job(job)

            logger.info(
                f"{self.worker_id} processing job {job_id} "
                f"(attempt {job.retry_count + 1}/{job.max_retries + 1})"
            )

            # Execute workflow with retry logic
            await self._execute_with_retry(job)

        except Exception as e:
            logger.error(f"{self.worker_id} unexpected error processing job {job_id}: {e}")

            # Try to mark job as failed
            try:
                job = await self.job_repository.get_job(job_id)
                if job:
                    job.fail(str(e))
                    await self.job_repository.save_job(job)
            except Exception as save_error:
                logger.error(f"Failed to save error status for job {job_id}: {save_error}")

    async def _execute_with_retry(self, job: ProcessingJob):
        """
        Execute job workflow with exponential backoff retry.

        Args:
            job: Job to process

        Retry strategy:
            - Attempt 1: Immediate
            - Attempt 2: 2 seconds delay
            - Attempt 3: 4 seconds delay
            - Attempt 4: 8 seconds delay (final)
        """
        last_error = None

        while job.retry_count <= job.max_retries:
            try:
                # Update status to processing
                if job.status == JobStatus.PENDING:
                    job.update_status(JobStatus.DOWNLOADING)
                    await self.job_repository.save_job(job)

                # Execute the workflow
                await self._execute_workflow(job)

                # Job completed successfully
                logger.info(
                    f"{self.worker_id} completed job {job.id} "
                    f"(duration: {job.duration:.1f}s)"
                )
                return

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"{self.worker_id} job {job.id} failed "
                    f"(attempt {job.retry_count + 1}/{job.max_retries + 1}): {e}"
                )

                # Check if we can retry
                if job.can_retry():
                    # Increment retry count and calculate delay
                    job.increment_retry(last_error)
                    await self.job_repository.save_job(job)

                    # Exponential backoff delay
                    delay = 2 ** job.retry_count  # 2, 4, 8 seconds
                    logger.info(
                        f"{self.worker_id} retrying job {job.id} "
                        f"in {delay} seconds (attempt {job.retry_count + 1}/{job.max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                else:
                    # Max retries exceeded, mark as failed
                    job.fail(f"Max retries exceeded. Last error: {last_error}")
                    await self.job_repository.save_job(job)
                    logger.error(
                        f"{self.worker_id} job {job.id} permanently failed "
                        f"after {job.retry_count} retries"
                    )
                    return

    async def _execute_workflow(self, job: ProcessingJob):
        """
        Execute workflow based on job type.

        Args:
            job: Job to process

        Raises:
            Exception: If workflow execution fails
        """
        # Route to appropriate workflow based on job type
        if job.job_type and job.job_type.value == "youtube_url":
            await self._process_youtube_workflow(job)
        elif job.job_type and job.job_type.value == "local_file":
            await self._process_local_file_workflow(job)
        else:
            raise ValueError(f"Unknown job type: {job.job_type}")

    async def _process_youtube_workflow(self, job: ProcessingJob):
        """
        Process YouTube URL workflow.

        Args:
            job: Job with YouTube URL

        Note:
            This integrates with the existing WorkflowService to execute
            the full transcription pipeline.
        """
        from pathlib import Path

        # Prepare output directory
        output_dir = Path(job.output_directory) if job.output_directory else None

        # Execute workflow (this will update job status internally)
        # Note: workflow service now returns the job object, not a dict
        await self.workflow_service.process_youtube_url(
            url=job.input_path,
            output_dir=output_dir,
            format=job.subtitle_format,
            keep_audio=job.keep_audio,
            enable_translation=job.enable_translation,
            translation_target_language=job.translation_target_language,
            whisper_source_language=job.whisper_source_language,
            whisper_model=job.whisper_model,
            whisper_base_url=job.whisper_base_url,
            job=job
        )

        # Job status is updated internally by workflow service
        # Save the final state
        await self.job_repository.save_job(job)

    async def _process_local_file_workflow(self, job: ProcessingJob):
        """
        Process local file workflow.

        Args:
            job: Job with local file path
        """
        from pathlib import Path

        # Prepare output directory
        output_dir = Path(job.output_directory) if job.output_directory else None

        # Execute workflow (this will update job status internally)
        # Note: workflow service now returns the job object, not a dict
        await self.workflow_service.process_local_file(
            file_path=Path(job.input_path),
            output_dir=output_dir,
            format=job.subtitle_format,
            keep_audio=job.keep_audio,
            enable_translation=job.enable_translation,
            translation_target_language=job.translation_target_language,
            whisper_source_language=job.whisper_source_language,
            whisper_model=job.whisper_model,
            whisper_base_url=job.whisper_base_url,
            job=job
        )

        # Job status is updated internally by workflow service
        # Save the final state
        await self.job_repository.save_job(job)

    def get_stats(self) -> dict:
        """
        Get worker statistics.

        Returns:
            Dictionary with worker stats
        """
        return {
            "worker_id": self.worker_id,
            "running": self._running,
            "active_jobs": len(self._tasks),
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "queue_available_slots": self.max_concurrent_jobs - len(self._tasks)
        }
