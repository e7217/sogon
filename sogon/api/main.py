"""FastAPI application for SOGON API server"""

import logging
import uuid
from datetime import datetime
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, HttpUrl

from .config import config
from ..models.translation import SupportedLanguage
from ..models.job import JobStatus
from ..config import get_settings
from ..services.interfaces import (
    AudioService, TranscriptionService, CorrectionService,
    YouTubeService, FileService, WorkflowService, TranslationService
)
from ..services.audio_service import AudioServiceImpl
from ..services.transcription_service import TranscriptionServiceImpl
from ..services.workflow_service import WorkflowServiceImpl
from ..repositories.interfaces import FileRepository
from ..repositories.file_repository import FileRepositoryImpl
import asyncio

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="SOGON API",
    description="Subtitle generator API from media URLs or local audio files",
    version="1.0.0",
    debug=config.debug
)


# Request/Response Models
class TranscribeRequest(BaseModel):
    """Transcribe request model for URL input"""
    url: HttpUrl
    enable_correction: bool = False
    use_ai_correction: bool = False
    subtitle_format: str = "txt"
    keep_audio: bool = False
    enable_translation: bool = False
    translation_target_language: Optional[str] = None
    whisper_source_language: Optional[str] = None
    whisper_model: Optional[str] = None
    whisper_base_url: Optional[str] = None


class TranscribeResponse(BaseModel):
    """Transcribe response model"""
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    """Job status response model"""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: Optional[int] = None
    message: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    version: str
    config: dict


# In-memory job storage (in production, use Redis or database)
jobs = {}


class APIServiceContainer:
    """Dependency injection container for API services"""

    def __init__(self):
        self.settings = get_settings()
        self._file_repository: Optional[FileRepository] = None
        self._audio_service: Optional[AudioService] = None
        self._transcription_service: Optional[TranscriptionService] = None
        self._correction_service: Optional[CorrectionService] = None
        self._youtube_service: Optional[YouTubeService] = None
        self._file_service: Optional[FileService] = None
        self._translation_service: Optional[TranslationService] = None
        self._workflow_service: Optional[WorkflowService] = None

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
            self._transcription_service = TranscriptionServiceImpl(
                api_key=self.settings.openai_api_key,
                max_workers=self.settings.max_workers
            )
        return self._transcription_service

    @property
    def correction_service(self) -> CorrectionService:
        if self._correction_service is None:
            if not self.settings.openai_api_key:
                raise ValueError("OpenAI API key is required for correction service. Set OPENAI_API_KEY environment variable.")
            from ..services.correction_service import CorrectionServiceImpl
            self._correction_service = CorrectionServiceImpl(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                model=self.settings.openai_model,
                temperature=self.settings.openai_temperature
            )
        return self._correction_service

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
            if not self.settings.openai_api_key:
                raise ValueError("OpenAI API key is required for translation service. Set OPENAI_API_KEY environment variable.")
            from ..services.translation_service import TranslationServiceImpl
            self._translation_service = TranslationServiceImpl(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                model=self.settings.openai_model,
                temperature=self.settings.openai_temperature,
                max_concurrent_requests=self.settings.openai_max_concurrent_requests
            )
        return self._translation_service

    @property
    def workflow_service(self) -> WorkflowService:
        if self._workflow_service is None:
            self._workflow_service = WorkflowServiceImpl(
                audio_service=self.audio_service,
                transcription_service=self.transcription_service,
                correction_service=self.correction_service,
                youtube_service=self.youtube_service,
                file_service=self.file_service,
                translation_service=self.translation_service
            )
        return self._workflow_service


# Service container for dependency injection
services = APIServiceContainer()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    
    try:
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            config={
                "host": config.host,
                "port": config.port,
                "debug": config.debug,
                "base_output_dir": config.base_output_dir,
                "enable_correction": config.enable_correction,
                "use_ai_correction": config.use_ai_correction
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


def update_job_safely(job_id: str, updates: dict) -> bool:
    """Safely update job status with race condition protection"""
    if job_id in jobs:
        try:
            jobs[job_id].update(updates)
            return True
        except KeyError:
            # Job was deleted between the check and update
            logger.warning(f"Job {job_id} was deleted during update")
            return False
    else:
        logger.warning(f"Job {job_id} not found during update")
        return False


async def process_transcription_task(
    job_id: str,
    input_path: str,
    enable_correction: bool,
    use_ai_correction: bool,
    subtitle_format: str,
    keep_audio: bool = False,
    enable_translation: bool = False,
    translation_target_language: Optional[str] = None,
    whisper_source_language: Optional[str] = None,
    whisper_model: Optional[str] = None,
    whisper_base_url: Optional[str] = None
):
    """Background task for processing transcription"""
    try:
        logger.info(f"Starting transcription job {job_id}")
        
        # Safely update job status to processing
        if not update_job_safely(job_id, {"status": "processing", "progress": 0}):
            logger.info(f"Job {job_id} was cancelled before processing started")
            return
        
        # Process the transcription using workflow service directly
        base_output_dir = Path(config.base_output_dir)

        # Parse translation target language
        target_lang = None
        if enable_translation and translation_target_language:
            try:
                target_lang = SupportedLanguage(translation_target_language)
            except ValueError:
                raise Exception(f"Unsupported translation language: {translation_target_language}")

        # Check if input is URL or local file
        if services.youtube_service.is_valid_url(input_path):
            job = await services.workflow_service.process_youtube_url(
                url=input_path,
                output_dir=base_output_dir,
                format=subtitle_format,
                enable_correction=enable_correction,
                use_ai_correction=use_ai_correction,
                keep_audio=keep_audio,
                enable_translation=enable_translation,
                translation_target_language=target_lang,
                whisper_source_language=whisper_source_language,
                whisper_model=whisper_model,
                whisper_base_url=whisper_base_url
            )
        else:
            # Local file processing
            file_path = Path(input_path)
            if not file_path.exists():
                raise Exception(f"File not found: {file_path}")

            job = await services.workflow_service.process_local_file(
                file_path=file_path,
                output_dir=base_output_dir,
                format=subtitle_format,
                enable_correction=enable_correction,
                use_ai_correction=use_ai_correction,
                keep_audio=keep_audio,
                enable_translation=enable_translation,
                translation_target_language=target_lang,
                whisper_source_language=whisper_source_language,
                whisper_model=whisper_model,
                whisper_base_url=whisper_base_url
            )

        # Wait for job completion (with timeout)
        max_wait_seconds = services.settings.max_processing_timeout_seconds
        wait_seconds = 0

        while wait_seconds < max_wait_seconds:
            status = await services.workflow_service.get_job_status(job.id)

            if status == JobStatus.COMPLETED:
                break
            elif status == JobStatus.FAILED:
                raise Exception(f"Processing failed: {job.error_message}")
            elif status == JobStatus.NOT_FOUND:
                raise Exception("Job not found")

            # Wait and check again
            await asyncio.sleep(2)
            wait_seconds += 2

        if wait_seconds >= max_wait_seconds:
            raise Exception("Processing timed out")
        
        # Safely update job completion status
        if not update_job_safely(job_id, {
            "progress": 100,
            "status": "completed",
            "result": {
                "message": "Transcription completed successfully",
                "output_directory": str(job.actual_output_dir) if job.actual_output_dir else str(base_output_dir),
                "job_details": {
                    "format": subtitle_format,
                    "correction_enabled": enable_correction,
                    "ai_correction_enabled": use_ai_correction,
                    "translation_enabled": enable_translation,
                    "whisper_model": whisper_model,
                    "whisper_base_url": whisper_base_url
                }
            }
        }):
            logger.info(f"Job {job_id} was cancelled during processing")
            return
            
        logger.info(f"Transcription job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Transcription job {job_id} failed: {e}")
        # Safely update job failure status
        update_job_safely(job_id, {"status": "failed", "error": str(e)})


@app.post("/api/v1/transcribe/url", response_model=TranscribeResponse)
async def transcribe_url(request: TranscribeRequest, background_tasks: BackgroundTasks):
    """Submit URL for transcription"""
    job_id = str(uuid.uuid4())

    # Get settings for default values
    settings = get_settings()

    # Apply default correction settings if not explicitly set
    effective_correction = request.enable_correction or settings.enable_correction_by_default
    effective_ai_correction = request.use_ai_correction or (effective_correction and settings.enable_correction_by_default)

    # Initialize job
    jobs[job_id] = {
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "progress": 0,
        "input_type": "url",
        "input_value": str(request.url)
    }

    # Add background task
    background_tasks.add_task(
        process_transcription_task,
        job_id,
        str(request.url),
        effective_correction,
        effective_ai_correction,
        request.subtitle_format,
        request.keep_audio,
        request.enable_translation,
        request.translation_target_language,
        request.whisper_source_language,
        request.whisper_model,
        request.whisper_base_url
    )
    
    logger.info(f"Created transcription job {job_id} for URL: {request.url}")
    
    return TranscribeResponse(
        job_id=job_id,
        status="pending",
        message="Transcription job created successfully"
    )


@app.post("/api/v1/transcribe/upload", response_model=TranscribeResponse)
async def transcribe_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    enable_correction: bool = Form(False),
    use_ai_correction: bool = Form(False),
    subtitle_format: str = Form("txt"),
    keep_audio: bool = Form(False),
    enable_translation: bool = Form(False),
    translation_target_language: Optional[str] = Form(None),
    whisper_source_language: Optional[str] = Form(None),
    whisper_model: Optional[str] = Form(None),
    whisper_base_url: Optional[str] = Form(None)
):
    """Upload file for transcription"""
    job_id = str(uuid.uuid4())

    # Get settings for default values
    settings = get_settings()

    # Apply default correction settings if not explicitly set
    effective_correction = enable_correction or settings.enable_correction_by_default
    effective_ai_correction = use_ai_correction or (effective_correction and settings.enable_correction_by_default)

    # Save uploaded file
    upload_dir = Path(config.base_output_dir) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / f"{job_id}_{file.filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Initialize job
        jobs[job_id] = {
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "progress": 0,
            "input_type": "file",
            "input_value": str(file_path),
            "original_filename": file.filename
        }
        
        # Add background task
        background_tasks.add_task(
            process_transcription_task,
            job_id,
            str(file_path),
            effective_correction,
            effective_ai_correction,
            subtitle_format,
            keep_audio,
            enable_translation,
            translation_target_language,
            whisper_source_language,
            whisper_model,
            whisper_base_url
        )
        
        logger.info(f"Created transcription job {job_id} for uploaded file: {file.filename}")
        
        return TranscribeResponse(
            job_id=job_id,
            status="pending",
            message="File uploaded and transcription job created successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")


@app.get("/api/v1/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get job status and progress"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress"),
        message=job.get("message"),
        result=job.get("result"),
        error=job.get("error")
    )


@app.get("/api/v1/jobs/{job_id}/download")
async def download_result(job_id: str, file_type: str = "original"):
    """Download transcription result files"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    result = job.get("result")
    if not result:
        raise HTTPException(status_code=404, detail="No result available")
    
    if file_type == "original" and result.get("original_files"):
        file_path = result["original_files"][0]  # subtitle file
    elif file_type == "corrected" and result.get("corrected_files"):
        file_path = result["corrected_files"][0]  # corrected subtitle file
    elif file_type == "translated" and result.get("translated_files"):
        file_path = result["translated_files"][0]  # translated subtitle file
    else:
        raise HTTPException(status_code=404, detail="Requested file type not available")
    
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=Path(file_path).name,
        media_type="text/plain"
    )


@app.delete("/api/v1/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete/cancel job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Clean up files if needed
    job = jobs[job_id]
    if job.get("input_type") == "file":
        try:
            file_path = Path(job["input_value"])
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete uploaded file: {e}")
    
    del jobs[job_id]
    
    return {"message": "Job deleted successfully"}


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
    return {"message": "SOGON API Server", "docs": "/docs"}


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
