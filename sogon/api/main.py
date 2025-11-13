"""FastAPI application for SOGON API server with async job queue"""

import logging
import uuid
from datetime import datetime
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from .config import config
from .schemas.requests import CreateJobRequest
from .schemas.responses import (
    JobCreatedResponse, JobStatusResponse, JobListResponse,
    ErrorResponse
)
from ..models.translation import SupportedLanguage
from ..models.job import ProcessingJob, JobStatus, JobType
from ..config import get_settings
from ..services.interfaces import (
    AudioService, TranscriptionService,
    YouTubeService, FileService, WorkflowService, TranslationService
)
from ..services.audio_service import AudioServiceImpl
from ..services.transcription_service import TranscriptionServiceImpl
from ..services.workflow_service import WorkflowServiceImpl
from ..repositories.interfaces import FileRepository, JobRepository
from ..repositories.file_repository import FileRepositoryImpl
from ..repositories.job_repository import FileBasedJobRepository
from ..queue.factory import create_queue
from ..queue.interface import JobQueue
from ..workers.job_worker import JobWorker
from ..utils.provider_factory import get_transcription_provider
from ..utils.logging import setup_logging

# Configure logging with unified format
setup_logging(console_level=config.log_level)
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    version: str
    config: dict


class APIServiceContainer:
    """Dependency injection container for API services"""

    def __init__(self):
        self.settings = get_settings()
        self._file_repository: Optional[FileRepository] = None
        self._audio_service: Optional[AudioService] = None
        self._transcription_service: Optional[TranscriptionService] = None
        self._youtube_service: Optional[YouTubeService] = None
        self._file_service: Optional[FileService] = None
        self._translation_service: Optional[TranslationService] = None
        self._workflow_service: Optional[WorkflowService] = None
        self._job_repository: Optional[JobRepository] = None
        self._queue: Optional[JobQueue] = None
        self._worker: Optional[JobWorker] = None
        self._worker_task: Optional[asyncio.Task] = None

    @property
    def file_repository(self) -> FileRepository:
        if self._file_repository is None:
            self._file_repository = FileRepositoryImpl()
        return self._file_repository

    @property
    def audio_service(self) -> AudioService:
        if self._audio_service is None:
            self._audio_service = AudioServiceImpl(
                max_workers=self.settings.max_workers
            )
        return self._audio_service

    @property
    def transcription_service(self) -> TranscriptionService:
        if self._transcription_service is None:
            # Use unified provider pattern (matches CLI implementation)
            provider = get_transcription_provider(self.settings)

            # Log warning if using API-based provider without API key
            if provider is None and not self.settings.effective_transcription_api_key:
                logger.warning("Transcription API key not set. Transcription service may not work properly.")

            self._transcription_service = TranscriptionServiceImpl(
                max_workers=self.settings.max_workers,
                provider=provider
            )
        return self._transcription_service

    @property
    def youtube_service(self) -> YouTubeService:
        if self._youtube_service is None:
            from ..services.youtube_service import YouTubeServiceImpl
            self._youtube_service = YouTubeServiceImpl(
                timeout=self.settings.youtube_socket_timeout,
                retries=self.settings.youtube_retries,
                preferred_format=self.settings.youtube_preferred_format
            )
        return self._youtube_service

    @property
    def file_service(self) -> FileService:
        if self._file_service is None:
            from ..services.file_service import FileServiceImpl
            self._file_service = FileServiceImpl(
                file_repository=self.file_repository,
                output_base_dir=Path(self.settings.output_base_dir)
            )
        return self._file_service

    @property
    def translation_service(self) -> TranslationService:
        if self._translation_service is None:
            from ..services.translation_service import TranslationServiceImpl
            # Use same pattern as CLI - let service load settings internally
            self._translation_service = TranslationServiceImpl()
        return self._translation_service

    @property
    def workflow_service(self) -> WorkflowService:
        if self._workflow_service is None:
            # Translation service is optional - only initialize if API key is set
            translation_svc = self.translation_service  # Will return None if no API key

            self._workflow_service = WorkflowServiceImpl(
                audio_service=self.audio_service,
                transcription_service=self.transcription_service,
                youtube_service=self.youtube_service,
                file_service=self.file_service,
                translation_service=translation_svc
            )
        return self._workflow_service

    @property
    def job_repository(self) -> JobRepository:
        if self._job_repository is None:
            self._job_repository = FileBasedJobRepository()
        return self._job_repository

    @property
    def queue(self) -> JobQueue:
        if self._queue is None:
            self._queue = create_queue(backend="memory", max_size=150)
        return self._queue

    @property
    def worker(self) -> JobWorker:
        if self._worker is None:
            self._worker = JobWorker(
                queue=self.queue,
                job_repository=self.job_repository,
                workflow_service=self.workflow_service,
                max_concurrent_jobs=6,
                worker_id="worker-1"
            )
        return self._worker

    async def start_worker(self):
        """Start background worker"""
        if self._worker_task is None:
            logger.info("Starting background worker...")
            self._worker_task = asyncio.create_task(self.worker.start())

    async def stop_worker(self):
        """Stop background worker"""
        if self._worker_task is not None:
            logger.info("Stopping background worker...")
            await self.worker.stop()
            try:
                await asyncio.wait_for(self._worker_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Worker shutdown timed out")
            self._worker_task = None


# Service container for dependency injection
services = APIServiceContainer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting SOGON API application...")
    await services.start_worker()
    logger.info("Background worker started")

    yield

    # Shutdown
    logger.info("Shutting down SOGON API application...")
    await services.stop_worker()
    logger.info("Background worker stopped")


# FastAPI app instance
app = FastAPI(
    title="SOGON API",
    description="Async subtitle generator API from media URLs or local audio files",
    version="2.0.0",
    debug=config.debug,
    lifespan=lifespan
)


def get_base_url(request: Request) -> str:
    """Extract base URL from request"""
    return f"{request.url.scheme}://{request.url.netloc}"


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")

    try:
        # Get repository and worker stats
        repo_stats = await services.job_repository.get_stats()
        worker_stats = services.worker.get_stats()

        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            version="2.0.0",
            config={
                "host": config.host,
                "port": config.port,
                "debug": config.debug,
                "base_output_dir": config.base_output_dir,
                "worker_status": worker_stats,
                "repository_stats": repo_stats
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.post(
    "/api/v1/jobs",
    response_model=JobCreatedResponse,
    status_code=202,
    responses={
        202: {"description": "Job created and queued"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Queue full"}
    }
)
async def create_job(request: Request, job_request: CreateJobRequest):
    """
    Create transcription job (unified endpoint for URL and file upload).

    Returns 202 Accepted with job_id for status polling.
    """
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())

        # Determine job type and input
        if job_request.url:
            job_type = JobType.YOUTUBE_URL
            input_path = str(job_request.url)
        else:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error="invalid_input",
                    detail="Either 'url' must be provided or file must be uploaded"
                ).model_dump()
            )

        # Validate whisper_model if provided
        if job_request.whisper_model and not job_request.whisper_model.startswith("whisper"):
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error="invalid_model",
                    detail=f"Invalid Whisper model: {job_request.whisper_model}. Must be a Whisper model (e.g., whisper-large-v3-turbo)"
                ).model_dump()
            )

        # Parse translation target language
        target_lang = None
        if job_request.enable_translation and job_request.translation_target_language:
            try:
                target_lang = SupportedLanguage(job_request.translation_target_language)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content=ErrorResponse(
                        error="invalid_language",
                        detail=f"Unsupported translation language: {job_request.translation_target_language}"
                    ).model_dump()
                )

        # Create job
        job = ProcessingJob(
            id=job_id,
            job_type=job_type,
            input_path=input_path,
            output_directory=config.base_output_dir,
            subtitle_format=job_request.subtitle_format,
            keep_audio=job_request.keep_audio,
            enable_translation=job_request.enable_translation,
            translation_target_language=target_lang,
            whisper_source_language=job_request.whisper_source_language,
            whisper_model=job_request.whisper_model,
            whisper_base_url=str(job_request.whisper_base_url) if job_request.whisper_base_url else None
        )

        # Save to repository
        saved = await services.job_repository.save_job(job)
        if not saved:
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error="save_failed",
                    detail="Failed to save job to repository"
                ).model_dump()
            )

        # Enqueue job
        job.mark_enqueued()
        enqueued = await services.queue.enqueue(job_id)
        if not enqueued:
            # Queue is full
            await services.job_repository.delete_job(job_id)
            return JSONResponse(
                status_code=503,
                content=ErrorResponse(
                    error="queue_full",
                    detail="Job queue is at capacity. Please try again later."
                ).model_dump()
            )

        # Save enqueued timestamp
        await services.job_repository.save_job(job)

        logger.info(f"Created and enqueued job {job_id} for {job_type.value}: {input_path}")

        # Return 202 Accepted with HATEOAS links
        base_url = get_base_url(request)
        response = JobCreatedResponse.from_job(
            job_id=job_id,
            base_url=base_url,
            created_at=job.created_at
        )
        return JSONResponse(
            status_code=202,
            content=response.model_dump(mode='json')
        )

    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="internal_error",
                detail=str(e)
            ).model_dump(mode='json')
        )


@app.post(
    "/api/v1/jobs/upload",
    response_model=JobCreatedResponse,
    status_code=202,
    responses={
        202: {"description": "Job created and queued"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Queue full"}
    }
)
async def create_job_upload(
    request: Request,
    file: UploadFile = File(...),
    subtitle_format: str = Form("txt"),
    keep_audio: bool = Form(False),
    enable_translation: bool = Form(False),
    translation_target_language: Optional[str] = Form(None),
    whisper_source_language: Optional[str] = Form(None),
    whisper_model: Optional[str] = Form(None),
    whisper_base_url: Optional[str] = Form(None)
):
    """
    Upload file for transcription.

    Returns 202 Accepted with job_id for status polling.
    """
    try:

        # Generate job ID
        job_id = str(uuid.uuid4())

        # Save uploaded file
        upload_dir = Path(config.base_output_dir) / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / f"{job_id}_{file.filename}"

        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Parse translation target language
        target_lang = None
        if enable_translation and translation_target_language:
            try:
                target_lang = SupportedLanguage(translation_target_language)
            except ValueError:
                file_path.unlink()  # Clean up uploaded file
                return JSONResponse(
                    status_code=400,
                    content=ErrorResponse(
                        error="invalid_language",
                        detail=f"Unsupported translation language: {translation_target_language}"
                    ).model_dump()
                )

        # Create job
        job = ProcessingJob(
            id=job_id,
            job_type=JobType.LOCAL_FILE,
            input_path=str(file_path),
            output_directory=config.base_output_dir,
            subtitle_format=subtitle_format,
            keep_audio=keep_audio,
            enable_translation=enable_translation,
            translation_target_language=target_lang,
            whisper_source_language=whisper_source_language,
            whisper_model=whisper_model,
            whisper_base_url=whisper_base_url
        )

        # Save to repository
        saved = await services.job_repository.save_job(job)
        if not saved:
            file_path.unlink()  # Clean up uploaded file
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error="save_failed",
                    detail="Failed to save job to repository"
                ).model_dump()
            )

        # Enqueue job
        job.mark_enqueued()
        enqueued = await services.queue.enqueue(job_id)
        if not enqueued:
            # Queue is full
            await services.job_repository.delete_job(job_id)
            file_path.unlink()  # Clean up uploaded file
            return JSONResponse(
                status_code=503,
                content=ErrorResponse(
                    error="queue_full",
                    detail="Job queue is at capacity. Please try again later."
                ).model_dump()
            )

        # Save enqueued timestamp
        await services.job_repository.save_job(job)

        logger.info(f"Created and enqueued job {job_id} for uploaded file: {file.filename}")

        # Return 202 Accepted with HATEOAS links
        base_url = get_base_url(request)
        response = JobCreatedResponse.from_job(
            job_id=job_id,
            base_url=base_url,
            created_at=job.created_at
        )
        return JSONResponse(
            status_code=202,
            content=response.model_dump(mode='json')
        )

    except Exception as e:
        logger.error(f"Failed to create upload job: {e}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="internal_error",
                detail=str(e)
            ).model_dump(mode='json')
        )


@app.get(
    "/api/v1/jobs/{job_id}",
    response_model=JobStatusResponse,
    responses={
        200: {"description": "Job status"},
        404: {"model": ErrorResponse, "description": "Job not found"}
    }
)
async def get_job_status(request: Request, job_id: str):
    """Get job status and progress (polling endpoint)"""
    job = await services.job_repository.get_job(job_id)

    if not job:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="job_not_found",
                detail=f"Job with ID {job_id} not found",
                job_id=job_id
            ).model_dump(mode='json')
        )

    # Build progress info
    progress_info = None
    if job.progress is not None:
        progress_info = {
            "percentage": job.progress,
            "current_step": job.status.value,
            "message": job.current_step_description
        }

    # Build result info (only for completed jobs)
    result_info = None
    if job.status == JobStatus.COMPLETED and job.original_files:
        result_info = {
            "output_directory": job.actual_output_dir or job.output_directory,
            "files": [],
            "translation_performed": job.enable_translation,
            "processing_duration_seconds": job.duration
        }

        # Add original files
        for file_path in job.original_files.values():
            if Path(file_path).exists():
                result_info["files"].append({
                    "type": "subtitle",
                    "format": job.subtitle_format,
                    "size_bytes": Path(file_path).stat().st_size
                })

    # Build HATEOAS links
    base_url = get_base_url(request)
    links = {
        "self": f"{base_url}/api/v1/jobs/{job_id}"
    }

    if job.status == JobStatus.COMPLETED:
        links["result"] = f"{base_url}/api/v1/jobs/{job_id}/result"
        links["download"] = f"{base_url}/api/v1/jobs/{job_id}/download"
    elif not job.status.is_terminal:
        links["cancel"] = f"{base_url}/api/v1/jobs/{job_id}"

    return JobStatusResponse(
        job_id=job_id,
        status=job.status.value,
        progress=progress_info,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        result=result_info,
        error=job.error_message,
        links=links
    )


@app.get(
    "/api/v1/jobs",
    response_model=JobListResponse,
    responses={
        200: {"description": "Job list"}
    }
)
async def list_jobs(
    request: Request,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List jobs with filtering and pagination"""
    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = JobStatus(status)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error="invalid_status",
                    detail=f"Invalid status value: {status}"
                ).model_dump()
            )

    # Get jobs from repository
    jobs = await services.job_repository.list_jobs(
        status=status_filter,
        limit=limit,
        offset=offset
    )

    # Convert to response format
    base_url = get_base_url(request)
    job_responses = []

    for job in jobs:
        # Build progress info
        progress_info = None
        if job.progress is not None:
            progress_info = {
                "percentage": job.progress,
                "current_step": job.status.value,
                "message": job.current_step_description
            }

        # Build links
        links = {"self": f"{base_url}/api/v1/jobs/{job.id}"}

        job_responses.append(
            JobStatusResponse(
                job_id=job.id,
                status=job.status.value,
                progress=progress_info,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                result=None,  # Don't include full result in list
                error=job.error_message if job.status == JobStatus.FAILED else None,
                links=links
            )
        )

    # Build pagination links
    links = {
        "self": f"{base_url}/api/v1/jobs?limit={limit}&offset={offset}"
    }

    if status:
        links["self"] += f"&status={status}"

    if offset + limit < len(job_responses):
        next_offset = offset + limit
        links["next"] = f"{base_url}/api/v1/jobs?limit={limit}&offset={next_offset}"
        if status:
            links["next"] += f"&status={status}"

    return JobListResponse(
        jobs=job_responses,
        total=len(job_responses),
        limit=limit,
        offset=offset,
        links=links
    )


@app.delete(
    "/api/v1/jobs/{job_id}",
    responses={
        200: {"description": "Job cancelled/deleted"},
        404: {"model": ErrorResponse, "description": "Job not found"}
    }
)
async def delete_job(job_id: str):
    """Cancel/delete job"""
    job = await services.job_repository.get_job(job_id)

    if not job:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="job_not_found",
                detail=f"Job with ID {job_id} not found",
                job_id=job_id
            ).model_dump(mode='json')
        )

    # Mark as cancelled if not terminal
    if not job.status.is_terminal:
        job.cancel()
        await services.job_repository.save_job(job)

        # Try to cancel from queue
        await services.queue.cancel(job_id)

        logger.info(f"Cancelled job {job_id}")
        return {"message": "Job cancelled successfully"}
    else:
        # Delete terminal job
        await services.job_repository.delete_job(job_id)

        # Clean up uploaded file if exists
        if job.job_type == JobType.LOCAL_FILE:
            try:
                file_path = Path(job.input_path)
                if file_path.exists() and "uploads" in str(file_path):
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete uploaded file: {e}")

        logger.info(f"Deleted job {job_id}")
        return {"message": "Job deleted successfully"}


@app.get("/api/v1/jobs/{job_id}/download")
async def download_result(job_id: str, file_type: str = "original"):
    """Download transcription result files"""
    job = await services.job_repository.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    # Get file path
    file_path = None
    if file_type == "original" and job.original_files:
        # Get subtitle file
        file_path = job.original_files.get("subtitle") or job.original_files.get("transcript")
    elif file_type == "translated" and job.translated_files:
        # Get translated subtitle file
        file_path = job.translated_files[0] if job.translated_files else None

    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Requested file not available")

    return FileResponse(
        path=file_path,
        filename=Path(file_path).name,
        media_type="text/plain"
    )


@app.get("/api/v1/languages")
async def get_supported_languages():
    """Get list of supported translation languages"""
    languages = []
    for lang in SupportedLanguage:
        languages.append({
            "code": lang.value,
            "name": lang.display_name
        })
    return {"supported_languages": languages}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SOGON API Server (Async)",
        "version": "2.0.0",
        "docs": "/docs"
    }


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(_, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting SOGON API server on {config.host}:{config.port}")
    uvicorn.run(
        "sogon.api.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )
