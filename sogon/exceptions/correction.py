"""
Text correction related exceptions
"""

from typing import Optional

from .base import SogonError, SogonRetryableError, SogonTimeoutError


class CorrectionError(SogonError):
    """Base exception for text correction-related errors"""
    
    def __init__(
        self,
        message: str,
        text_length: Optional[int] = None,
        correction_method: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="CORRECTION_ERROR", **kwargs)
        if text_length is not None:
            self.add_context("text_length", text_length)
        if correction_method:
            self.add_context("correction_method", correction_method)


class CorrectionAPIError(CorrectionError, SogonRetryableError):
    """Error when correction API calls fail"""
    
    def __init__(
        self,
        message: str,
        api_provider: Optional[str] = None,
        status_code: Optional[int] = None,
        api_error_code: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="CORRECTION_API_ERROR", **kwargs)
        if api_provider:
            self.add_context("api_provider", api_provider)
        if status_code:
            self.add_context("status_code", status_code)
        if api_error_code:
            self.add_context("api_error_code", api_error_code)


class GroqCorrectionAPIError(CorrectionAPIError):
    """Specific error for Groq API correction failures"""
    
    def __init__(
        self,
        message: str,
        groq_error_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            api_provider="groq",
            error_code="GROQ_CORRECTION_API_ERROR",
            **kwargs
        )
        if groq_error_type:
            self.add_context("groq_error_type", groq_error_type)


class CorrectionTimeoutError(CorrectionError, SogonTimeoutError):
    """Error when correction operations timeout"""
    
    def __init__(
        self,
        message: str,
        correction_method: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="CORRECTION_TIMEOUT",
            operation="text_correction",
            correction_method=correction_method,
            **kwargs
        )


class CorrectionModelError(CorrectionError):
    """Error with correction model configuration or availability"""
    
    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        available_models: Optional[list] = None,
        **kwargs
    ):
        super().__init__(message, error_code="CORRECTION_MODEL_ERROR", **kwargs)
        if model_name:
            self.add_context("model_name", model_name)
        if available_models:
            self.add_context("available_models", available_models)


class CorrectionQuotaError(CorrectionAPIError):
    """Error when correction API quota is exceeded"""
    
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
            error_code="CORRECTION_QUOTA_ERROR",
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


class CorrectionRateLimitError(CorrectionAPIError):
    """Error when correction API rate limit is exceeded"""
    
    def __init__(
        self,
        message: str,
        rate_limit: Optional[int] = None,
        retry_after: Optional[float] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="CORRECTION_RATE_LIMIT",
            retry_after_seconds=retry_after or 60,
            **kwargs
        )
        if rate_limit is not None:
            self.add_context("rate_limit", rate_limit)


class CorrectionAuthenticationError(CorrectionAPIError):
    """Error when correction API authentication fails"""
    
    def __init__(
        self,
        message: str,
        auth_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="CORRECTION_AUTH_ERROR", **kwargs)
        if auth_type:
            self.add_context("auth_type", auth_type)
        # Authentication errors are usually not retryable
        self.context.pop("retry_after_seconds", None)


class CorrectionFormatError(CorrectionError):
    """Error with correction response format"""
    
    def __init__(
        self,
        message: str,
        expected_format: Optional[str] = None,
        received_format: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="CORRECTION_FORMAT_ERROR", **kwargs)
        if expected_format:
            self.add_context("expected_format", expected_format)
        if received_format:
            self.add_context("received_format", received_format)


class CorrectionValidationError(CorrectionError):
    """Error when correction validation fails"""
    
    def __init__(
        self,
        message: str,
        validation_type: Optional[str] = None,
        original_length: Optional[int] = None,
        corrected_length: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, error_code="CORRECTION_VALIDATION_ERROR", **kwargs)
        if validation_type:
            self.add_context("validation_type", validation_type)
        if original_length is not None:
            self.add_context("original_length", original_length)
        if corrected_length is not None:
            self.add_context("corrected_length", corrected_length)


class CorrectionQualityError(CorrectionError):
    """Error when correction quality is insufficient"""
    
    def __init__(
        self,
        message: str,
        quality_score: Optional[float] = None,
        min_quality: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, error_code="CORRECTION_QUALITY_ERROR", **kwargs)
        if quality_score is not None:
            self.add_context("quality_score", quality_score)
        if min_quality is not None:
            self.add_context("min_quality", min_quality)


class CorrectionLanguageError(CorrectionError):
    """Error with language-specific correction"""
    
    def __init__(
        self,
        message: str,
        language: Optional[str] = None,
        supported_languages: Optional[list] = None,
        **kwargs
    ):
        super().__init__(message, error_code="CORRECTION_LANGUAGE_ERROR", **kwargs)
        if language:
            self.add_context("language", language)
        if supported_languages:
            self.add_context("supported_languages", supported_languages)