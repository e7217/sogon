"""
Transcription related exceptions
"""

from typing import Optional

from .base import SogonError, SogonRetryableError, SogonTimeoutError


class TranscriptionError(SogonError):
    """Base exception for transcription-related errors"""
    
    def __init__(
        self,
        message: str,
        audio_file: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="TRANSCRIPTION_ERROR", **kwargs)
        if audio_file:
            self.add_context("audio_file", audio_file)
        if model:
            self.add_context("model", model)


class TranscriptionAPIError(TranscriptionError, SogonRetryableError):
    """Error when transcription API calls fail"""
    
    def __init__(
        self,
        message: str,
        api_provider: Optional[str] = None,
        status_code: Optional[int] = None,
        api_error_code: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="TRANSCRIPTION_API_ERROR", **kwargs)
        if api_provider:
            self.add_context("api_provider", api_provider)
        if status_code:
            self.add_context("status_code", status_code)
        if api_error_code:
            self.add_context("api_error_code", api_error_code)


class GroqAPIError(TranscriptionAPIError):
    """Specific error for Groq API failures"""
    
    def __init__(
        self,
        message: str,
        groq_error_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message, 
            api_provider="groq",
            error_code="GROQ_API_ERROR", 
            **kwargs
        )
        if groq_error_type:
            self.add_context("groq_error_type", groq_error_type)


class TranscriptionTimeoutError(TranscriptionError, SogonTimeoutError):
    """Error when transcription operations timeout"""
    
    def __init__(
        self,
        message: str,
        chunk_number: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="TRANSCRIPTION_TIMEOUT",
            operation="transcription",
            **kwargs
        )
        if chunk_number is not None:
            self.add_context("chunk_number", chunk_number)


class TranscriptionModelError(TranscriptionError):
    """Error with transcription model configuration or availability"""
    
    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        available_models: Optional[list] = None,
        **kwargs
    ):
        super().__init__(message, error_code="TRANSCRIPTION_MODEL_ERROR", **kwargs)
        if model_name:
            self.add_context("model_name", model_name)
        if available_models:
            self.add_context("available_models", available_models)


class TranscriptionQuotaError(TranscriptionAPIError):
    """Error when API quota is exceeded"""
    
    def __init__(
        self,
        message: str,
        quota_type: Optional[str] = None,
        quota_limit: Optional[int] = None,
        quota_used: Optional[int] = None,
        reset_time: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="TRANSCRIPTION_QUOTA_ERROR",
            retry_after_seconds=3600,  # Default 1 hour retry
            **kwargs
        )
        if quota_type:
            self.add_context("quota_type", quota_type)
        if quota_limit is not None:
            self.add_context("quota_limit", quota_limit)
        if quota_used is not None:
            self.add_context("quota_used", quota_used)
        if reset_time:
            self.add_context("reset_time", reset_time)


class TranscriptionRateLimitError(TranscriptionAPIError):
    """Error when API rate limit is exceeded"""
    
    def __init__(
        self,
        message: str,
        rate_limit: Optional[int] = None,
        retry_after: Optional[float] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="TRANSCRIPTION_RATE_LIMIT",
            retry_after_seconds=retry_after or 60,
            **kwargs
        )
        if rate_limit is not None:
            self.add_context("rate_limit", rate_limit)


class TranscriptionAuthenticationError(TranscriptionAPIError):
    """Error when API authentication fails"""
    
    def __init__(
        self,
        message: str,
        auth_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="TRANSCRIPTION_AUTH_ERROR", **kwargs)
        if auth_type:
            self.add_context("auth_type", auth_type)
        # Authentication errors are usually not retryable
        self.context.pop("retry_after_seconds", None)


class TranscriptionFormatError(TranscriptionError):
    """Error with transcription response format"""
    
    def __init__(
        self,
        message: str,
        expected_format: Optional[str] = None,
        received_format: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="TRANSCRIPTION_FORMAT_ERROR", **kwargs)
        if expected_format:
            self.add_context("expected_format", expected_format)
        if received_format:
            self.add_context("received_format", received_format)


class TranscriptionEmptyError(TranscriptionError):
    """Error when transcription result is empty"""
    
    def __init__(
        self,
        message: str,
        chunk_number: Optional[int] = None,
        audio_duration: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, error_code="TRANSCRIPTION_EMPTY", **kwargs)
        if chunk_number is not None:
            self.add_context("chunk_number", chunk_number)
        if audio_duration is not None:
            self.add_context("audio_duration", audio_duration)


class TranscriptionQualityError(TranscriptionError):
    """Error when transcription quality is too low"""
    
    def __init__(
        self,
        message: str,
        confidence_score: Optional[float] = None,
        min_confidence: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, error_code="TRANSCRIPTION_QUALITY_ERROR", **kwargs)
        if confidence_score is not None:
            self.add_context("confidence_score", confidence_score)
        if min_confidence is not None:
            self.add_context("min_confidence", min_confidence)


class TranscriptionLanguageError(TranscriptionError):
    """Error with language detection or specification"""
    
    def __init__(
        self,
        message: str,
        detected_language: Optional[str] = None,
        expected_language: Optional[str] = None,
        supported_languages: Optional[list] = None,
        **kwargs
    ):
        super().__init__(message, error_code="TRANSCRIPTION_LANGUAGE_ERROR", **kwargs)
        if detected_language:
            self.add_context("detected_language", detected_language)
        if expected_language:
            self.add_context("expected_language", expected_language)
        if supported_languages:
            self.add_context("supported_languages", supported_languages)