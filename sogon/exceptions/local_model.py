"""
Local Whisper model-specific exceptions.

Error hierarchy for faster-whisper provider failures.
Each error includes actionable resolution steps (FR-025, FR-009).
"""

from typing import Optional
from .base import SogonError, SogonConfigurationError, SogonResourceError


class ProviderNotAvailableError(SogonError):
    """
    Error when local model provider dependencies are not met.

    Raised when:
    - faster-whisper not installed
    - torch not installed
    - Other required dependencies missing

    Resolution:
    - Install dependencies: `pip install sogon[local]`
    """

    def __init__(
        self,
        message: str,
        provider_name: Optional[str] = None,
        missing_dependencies: Optional[list[str]] = None,
        **kwargs
    ):
        super().__init__(message, error_code="PROVIDER_NOT_AVAILABLE", **kwargs)
        if provider_name:
            self.add_context("provider_name", provider_name)
        if missing_dependencies:
            self.add_context("missing_dependencies", missing_dependencies)
            self.add_context(
                "resolution",
                f"Install missing dependencies: pip install {' '.join(missing_dependencies)}"
            )


class DeviceNotAvailableError(SogonError):
    """
    Error when requested compute device (CUDA/MPS) is not available.

    Raised when:
    - CUDA requested but not detected
    - MPS requested on non-Apple Silicon
    - Device drivers missing

    Resolution:
    - Use --device cpu (fallback)
    - Install CUDA 11.8+ for GPU support
    - Update GPU drivers
    """

    def __init__(
        self,
        message: str,
        requested_device: Optional[str] = None,
        available_devices: Optional[list[str]] = None,
        **kwargs
    ):
        super().__init__(message, error_code="DEVICE_NOT_AVAILABLE", **kwargs)
        if requested_device:
            self.add_context("requested_device", requested_device)
        if available_devices:
            self.add_context("available_devices", available_devices)
            self.add_context(
                "resolution",
                f"Use one of: {', '.join(available_devices)} or install device drivers"
            )


class InsufficientDiskSpaceError(SogonResourceError):
    """
    Error when insufficient disk space for model download.

    Raised when:
    - Free space < model size + 500MB buffer
    - Download directory not writable

    Resolution:
    - Free up disk space
    - Use smaller model (--local-model tiny/base)
    - Change download directory
    """

    def __init__(
        self,
        message: str,
        required_gb: Optional[float] = None,
        available_gb: Optional[float] = None,
        model_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="INSUFFICIENT_DISK_SPACE", **kwargs)
        if required_gb is not None:
            self.add_context("required_gb", required_gb)
        if available_gb is not None:
            self.add_context("available_gb", available_gb)
        if model_name:
            self.add_context("model_name", model_name)

        if required_gb and available_gb:
            shortage_gb = required_gb - available_gb
            self.add_context(
                "resolution",
                f"Free up {shortage_gb:.1f} GB or use smaller model (--local-model tiny/base)"
            )


class ResourceExhaustedError(SogonResourceError):
    """
    Error when RAM/VRAM exceeds thresholds during transcription.

    Raised when:
    - RAM usage > 90%
    - VRAM usage > 90%
    - Insufficient memory for model

    Resolution:
    - Close other applications
    - Use smaller model
    - Reduce max_workers concurrency
    """

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        used_gb: Optional[float] = None,
        available_gb: Optional[float] = None,
        threshold_percent: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, error_code="RESOURCE_EXHAUSTED", **kwargs)
        if resource_type:
            self.add_context("resource_type", resource_type)
        if used_gb is not None:
            self.add_context("used_gb", used_gb)
        if available_gb is not None:
            self.add_context("available_gb", available_gb)
        if threshold_percent is not None:
            self.add_context("threshold_percent", threshold_percent)

        self.add_context(
            "resolution",
            "Close other applications, use smaller model (--local-model tiny/base), or reduce --max-workers"
        )


class ModelDownloadError(SogonError):
    """
    Error during model download from Hugging Face.

    Raised when:
    - Network connection fails
    - Hugging Face Hub unavailable
    - Invalid model repository

    Resolution:
    - Check internet connection
    - Retry download
    - Verify model name is valid
    """

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        hf_repo: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="MODEL_DOWNLOAD_ERROR",
            retry_after_seconds=60,
            **kwargs
        )
        if model_name:
            self.add_context("model_name", model_name)
        if hf_repo:
            self.add_context("hf_repo", hf_repo)
        self.add_context(
            "resolution",
            "Check internet connection and retry. Verify model name is correct."
        )


class ModelCorruptionError(SogonError):
    """
    Error when downloaded model fails validation.

    Raised when:
    - Hash mismatch during download
    - Incomplete download
    - Corrupted model files

    Resolution:
    - Re-download model (will auto-retry)
    - Clear cache and retry
    """

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        expected_hash: Optional[str] = None,
        actual_hash: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="MODEL_CORRUPTION", **kwargs)
        if model_name:
            self.add_context("model_name", model_name)
        if expected_hash:
            self.add_context("expected_hash", expected_hash)
        if actual_hash:
            self.add_context("actual_hash", actual_hash)
        self.add_context(
            "resolution",
            "Model will be re-downloaded automatically. If issue persists, clear cache."
        )


# Alias for backward compatibility
ConfigurationError = SogonConfigurationError
