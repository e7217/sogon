"""
Audio processing related exceptions
"""

from typing import Optional, Any
from pathlib import Path

from .base import SogonError, SogonRetryableError, SogonResourceError, SogonTimeoutError


class AudioError(SogonError):
    """Base exception for audio-related errors"""
    
    def __init__(
        self,
        message: str,
        audio_path: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="AUDIO_ERROR", **kwargs)
        if audio_path:
            self.add_context("audio_path", audio_path)


class AudioDownloadError(AudioError, SogonRetryableError):
    """Error during audio download from URL"""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, error_code="AUDIO_DOWNLOAD_ERROR", **kwargs)
        if url:
            self.add_context("url", url)
        if status_code:
            self.add_context("status_code", status_code)


class YouTubeDownloadError(AudioDownloadError):
    """Specific error for YouTube download failures"""
    
    def __init__(
        self,
        message: str,
        video_id: Optional[str] = None,
        video_title: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="YOUTUBE_DOWNLOAD_ERROR", **kwargs)
        if video_id:
            self.add_context("video_id", video_id)
        if video_title:
            self.add_context("video_title", video_title)


class AudioProcessingError(AudioError):
    """General audio processing error"""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="AUDIO_PROCESSING_ERROR", **kwargs)
        if operation:
            self.add_context("operation", operation)


class AudioSplittingError(AudioProcessingError):
    """Error during audio file splitting"""
    
    def __init__(
        self,
        message: str,
        chunk_number: Optional[int] = None,
        total_chunks: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, error_code="AUDIO_SPLITTING_ERROR", **kwargs)
        if chunk_number is not None:
            self.add_context("chunk_number", chunk_number)
        if total_chunks is not None:
            self.add_context("total_chunks", total_chunks)


class UnsupportedAudioFormatError(AudioError):
    """Error for unsupported audio formats"""
    
    def __init__(
        self,
        message: str,
        format_detected: Optional[str] = None,
        supported_formats: Optional[list] = None,
        **kwargs
    ):
        super().__init__(message, error_code="UNSUPPORTED_AUDIO_FORMAT", **kwargs)
        if format_detected:
            self.add_context("format_detected", format_detected)
        if supported_formats:
            self.add_context("supported_formats", supported_formats)


class AudioFileNotFoundError(AudioError, SogonResourceError):
    """Error when audio file is not found"""
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message, 
            error_code="AUDIO_FILE_NOT_FOUND",
            resource_type="file",
            resource_name=file_path,
            **kwargs
        )
        if file_path:
            path_obj = Path(file_path)
            self.add_context("file_name", path_obj.name)
            self.add_context("file_directory", str(path_obj.parent))
            self.add_context("file_exists", path_obj.exists())


class AudioCorruptedError(AudioError):
    """Error when audio file is corrupted or unreadable"""
    
    def __init__(
        self,
        message: str,
        corruption_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="AUDIO_CORRUPTED", **kwargs)
        if corruption_type:
            self.add_context("corruption_type", corruption_type)


class AudioPermissionError(AudioError, SogonResourceError):
    """Error when lacking permissions for audio file operations"""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        file_path: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="AUDIO_PERMISSION_ERROR",
            resource_type="file_permission",
            resource_name=file_path,
            **kwargs
        )
        if operation:
            self.add_context("operation", operation)


class AudioTimeoutError(AudioError, SogonTimeoutError):
    """Error when audio operations timeout"""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="AUDIO_TIMEOUT",
            operation=operation,
            timeout_seconds=timeout_seconds,
            **kwargs
        )


class FFmpegError(AudioProcessingError):
    """Error when FFmpeg operations fail"""
    
    def __init__(
        self,
        message: str,
        command: Optional[list] = None,
        return_code: Optional[int] = None,
        stderr: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="FFMPEG_ERROR", operation="ffmpeg", **kwargs)
        if command:
            self.add_context("ffmpeg_command", " ".join(command))
        if return_code is not None:
            self.add_context("return_code", return_code)
        if stderr:
            self.add_context("stderr", stderr)


class FFprobeError(AudioProcessingError):
    """Error when FFprobe operations fail"""
    
    def __init__(
        self,
        message: str,
        command: Optional[list] = None,
        return_code: Optional[int] = None,
        stderr: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="FFPROBE_ERROR", operation="ffprobe", **kwargs)
        if command:
            self.add_context("ffprobe_command", " ".join(command))
        if return_code is not None:
            self.add_context("return_code", return_code)
        if stderr:
            self.add_context("stderr", stderr)


class AudioSizeError(AudioError):
    """Error when audio file size is problematic"""
    
    def __init__(
        self,
        message: str,
        file_size_mb: Optional[float] = None,
        max_size_mb: Optional[float] = None,
        min_size_mb: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, error_code="AUDIO_SIZE_ERROR", **kwargs)
        if file_size_mb is not None:
            self.add_context("file_size_mb", file_size_mb)
        if max_size_mb is not None:
            self.add_context("max_size_mb", max_size_mb)
        if min_size_mb is not None:
            self.add_context("min_size_mb", min_size_mb)


class AudioDurationError(AudioError):
    """Error when audio duration is problematic"""
    
    def __init__(
        self,
        message: str,
        duration_seconds: Optional[float] = None,
        max_duration_seconds: Optional[float] = None,
        min_duration_seconds: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, error_code="AUDIO_DURATION_ERROR", **kwargs)
        if duration_seconds is not None:
            self.add_context("duration_seconds", duration_seconds)
        if max_duration_seconds is not None:
            self.add_context("max_duration_seconds", max_duration_seconds)
        if min_duration_seconds is not None:
            self.add_context("min_duration_seconds", min_duration_seconds)