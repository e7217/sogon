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
from .. import process_input_to_subtitle

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="SOGON API",
    description="Subtitle generator API from YouTube URLs or local audio files",
    version="1.0.0",
    debug=config.debug
)


# Request/Response Models
class TranscribeRequest(BaseModel):
    """Transcribe request model for URL input"""
    url: HttpUrl
    enable_correction: bool = True
    use_ai_correction: bool = True
    subtitle_format: str = "txt"


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


async def process_transcription_task(job_id: str, input_path: str, enable_correction: bool, use_ai_correction: bool, subtitle_format: str):
    """Background task for processing transcription"""
    try:
        logger.info(f"Starting transcription job {job_id}")
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 0
        
        # Process the transcription
        original_files, corrected_files, actual_output_dir = process_input_to_subtitle(
            input_path, config.base_output_dir, subtitle_format, enable_correction, use_ai_correction
        )
        
        jobs[job_id]["progress"] = 100
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = {
            "original_files": original_files,
            "corrected_files": corrected_files,
            "output_directory": actual_output_dir
        }
        
        logger.info(f"Transcription job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Transcription job {job_id} failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@app.post("/api/v1/transcribe/url", response_model=TranscribeResponse)
async def transcribe_url(request: TranscribeRequest, background_tasks: BackgroundTasks):
    """Submit URL for transcription"""
    job_id = str(uuid.uuid4())
    
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
        request.enable_correction,
        request.use_ai_correction,
        request.subtitle_format
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
    enable_correction: bool = Form(True),
    use_ai_correction: bool = Form(True),
    subtitle_format: str = Form("txt")
):
    """Upload file for transcription"""
    job_id = str(uuid.uuid4())
    
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
            enable_correction,
            use_ai_correction,
            subtitle_format
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
