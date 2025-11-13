"""API request schemas using Pydantic."""

from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Optional, Literal


class CreateJobRequest(BaseModel):
    """
    Unified job creation request for URL or file upload.

    Either provide 'url' (for YouTube/remote URL) or upload a file separately.
    File uploads should use multipart/form-data with these fields as Form parameters.
    """

    # Input (for URL-based jobs, mutually exclusive with file upload)
    url: Optional[HttpUrl] = Field(
        None,
        description="YouTube URL or remote media file URL to process"
    )

    # Processing options
    subtitle_format: Literal["txt", "srt", "vtt", "json"] = Field(
        default="txt",
        description="Output subtitle format"
    )
    keep_audio: bool = Field(
        default=False,
        description="Keep downloaded audio file after processing"
    )

    # Translation options
    enable_translation: bool = Field(
        default=False,
        description="Enable subtitle translation"
    )
    translation_target_language: Optional[str] = Field(
        None,
        description="Target language code for translation (required if enable_translation is True)"
    )

    # Whisper options
    whisper_source_language: Optional[str] = Field(
        None,
        description="Source language code for Whisper (None = auto-detect)"
    )
    whisper_model: Optional[str] = Field(
        None,
        description="Whisper model name (None = use default)"
    )
    whisper_base_url: Optional[HttpUrl] = Field(
        None,
        description="Custom Whisper API base URL (None = use default)"
    )

    @field_validator('translation_target_language')
    @classmethod
    def validate_translation_language(cls, v: Optional[str], info) -> Optional[str]:
        """Validate that translation_target_language is provided when translation is enabled."""
        if info.data.get('enable_translation') and not v:
            raise ValueError('translation_target_language is required when enable_translation is True')
        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "subtitle_format": "srt",
                    "enable_translation": True,
                    "translation_target_language": "en"
                },
                {
                    "url": "https://example.com/video.mp4",
                    "subtitle_format": "txt",
                    "keep_audio": False,
                    "whisper_source_language": "ko"
                }
            ]
        }


class JobListRequest(BaseModel):
    """Request parameters for listing jobs with filtering and pagination."""

    status: Optional[Literal["pending", "downloading", "splitting", "transcribing", "translating", "saving", "completed", "failed", "cancelled"]] = Field(
        None,
        description="Filter by job status"
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of jobs to return (1-100)"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of jobs to skip for pagination"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "status": "completed",
                    "limit": 10,
                    "offset": 0
                },
                {
                    "limit": 50,
                    "offset": 0
                }
            ]
        }
