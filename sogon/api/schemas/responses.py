"""API response schemas using Pydantic."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List, Literal
from datetime import datetime


class JobCreatedResponse(BaseModel):
    """202 Accepted response for job creation."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "created_at": "2025-01-15T10:30:00Z",
                "message": "Job created and queued for processing",
                "_links": {
                    "self": "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000",
                    "status": "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000",
                    "cancel": "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000"
                }
            }
        }
    )

    job_id: str = Field(..., description="Unique job identifier")
    status: Literal["pending"] = Field(default="pending", description="Initial job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    message: str = Field(
        default="Job created and queued for processing",
        description="Human-readable message"
    )
    links: Dict[str, str] = Field(..., alias="_links", description="HATEOAS links for job resources")

    @staticmethod
    def from_job(job_id: str, base_url: str, created_at: datetime) -> "JobCreatedResponse":
        """
        Create response from job data.

        Args:
            job_id: Job identifier
            base_url: API base URL
            created_at: Job creation timestamp

        Returns:
            JobCreatedResponse instance
        """
        return JobCreatedResponse(
            job_id=job_id,
            status="pending",
            created_at=created_at,
            links={
                "self": f"{base_url}/api/v1/jobs/{job_id}",
                "status": f"{base_url}/api/v1/jobs/{job_id}",
                "cancel": f"{base_url}/api/v1/jobs/{job_id}",
            }
        )


class JobProgressInfo(BaseModel):
    """Job progress information."""

    percentage: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    current_step: Optional[str] = Field(None, description="Current processing step")
    message: Optional[str] = Field(None, description="Progress details message")


class JobStatusResponse(BaseModel):
    """Job status with progress information."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "transcribing",
                    "progress": {
                        "percentage": 65,
                        "current_step": "transcribing",
                        "message": "Processing audio chunks"
                    },
                    "created_at": "2025-01-15T10:30:00Z",
                    "started_at": "2025-01-15T10:30:05Z",
                    "completed_at": None,
                    "result": None,
                    "error": None,
                    "_links": {
                        "self": "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000",
                        "cancel": "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000"
                    }
                },
                {
                    "job_id": "550e8400-e29b-41d4-a716-446655440001",
                    "status": "completed",
                    "progress": {
                        "percentage": 100,
                        "current_step": "completed",
                        "message": "Processing complete"
                    },
                    "created_at": "2025-01-15T10:25:00Z",
                    "started_at": "2025-01-15T10:25:05Z",
                    "completed_at": "2025-01-15T10:30:00Z",
                    "result": {
                        "output_directory": "result/20250115_102500_video_title",
                        "files": [
                            {"type": "subtitle", "format": "srt", "size_bytes": 12345}
                        ],
                        "translation_performed": True,
                        "processing_duration_seconds": 295.5
                    },
                    "error": None,
                    "_links": {
                        "self": "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440001",
                        "result": "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440001/result",
                        "download": "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440001/download"
                    }
                }
            ]
        }
    )

    job_id: str = Field(..., description="Unique job identifier")
    status: Literal["pending", "downloading", "splitting", "transcribing", "translating", "saving", "completed", "failed", "cancelled"] = Field(
        ..., description="Current job status"
    )
    progress: Optional[JobProgressInfo] = Field(None, description="Progress information (if available)")

    # Timestamps
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")

    # Results (only when completed)
    result: Optional["JobResultResponse"] = Field(None, description="Result information (only for completed jobs)")

    # Error information (only when failed)
    error: Optional[str] = Field(None, description="Error message (only for failed jobs)")

    # HATEOAS links
    links: Dict[str, str] = Field(..., alias="_links", description="Resource links")


class JobFileInfo(BaseModel):
    """Information about a result file."""

    type: str = Field(..., description="File type (subtitle, metadata, timestamps, etc.)")
    format: str = Field(..., description="File format (srt, txt, vtt, json)")
    size_bytes: Optional[int] = Field(None, description="File size in bytes")


class JobResultResponse(BaseModel):
    """Result information for completed job."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "output_directory": "result/20250115_102500_video_title",
                "files": [
                    {"type": "subtitle", "format": "srt", "size_bytes": 12345},
                    {"type": "metadata", "format": "json", "size_bytes": 1024}
                ],
                "translation_performed": True,
                "processing_duration_seconds": 295.5,
                "_links": {
                    "download_subtitle": "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/download?type=subtitle",
                    "download_metadata": "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/download?type=metadata"
                }
            }
        }
    )

    output_directory: str = Field(..., description="Output directory path")
    files: List[JobFileInfo] = Field(..., description="List of result files")
    translation_performed: bool = Field(..., description="Whether translation was performed")
    processing_duration_seconds: float = Field(..., description="Total processing time in seconds")

    # Download links
    links: Optional[Dict[str, str]] = Field(None, alias="_links", description="Download links for result files")


class JobListResponse(BaseModel):
    """Paginated job list response."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "jobs": [
                    {
                        "job_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "completed",
                        "progress": {"percentage": 100, "current_step": "completed"},
                        "created_at": "2025-01-15T10:25:00Z",
                        "started_at": "2025-01-15T10:25:05Z",
                        "completed_at": "2025-01-15T10:30:00Z",
                        "_links": {"self": "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000"}
                    }
                ],
                "total": 45,
                "limit": 50,
                "offset": 0,
                "_links": {
                    "self": "http://localhost:8000/api/v1/jobs?limit=50&offset=0",
                    "next": "http://localhost:8000/api/v1/jobs?limit=50&offset=50"
                }
            }
        }
    )

    jobs: List[JobStatusResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs matching filter")
    limit: int = Field(..., description="Maximum jobs per page")
    offset: int = Field(..., description="Current offset")

    # Pagination links
    links: Dict[str, str] = Field(..., alias="_links", description="Pagination links")


class ErrorResponse(BaseModel):
    """Consistent error response format."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": "queue_full",
                    "detail": "Job queue is at capacity. Please try again later.",
                    "job_id": None,
                    "timestamp": "2025-01-15T10:30:00Z"
                },
                {
                    "error": "job_not_found",
                    "detail": "Job with ID 550e8400-e29b-41d4-a716-446655440000 not found",
                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                    "timestamp": "2025-01-15T10:30:00Z"
                },
                {
                    "error": "invalid_input",
                    "detail": "URL is not a valid YouTube or media file URL",
                    "job_id": None,
                    "timestamp": "2025-01-15T10:30:00Z"
                }
            ]
        }
    )

    error: str = Field(..., description="Error type or code")
    detail: str = Field(..., description="Human-readable error message")
    job_id: Optional[str] = Field(None, description="Related job ID (if applicable)")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
