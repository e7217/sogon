"""
Custom exception classes for sogon.

Provides specific exceptions for different error scenarios with actionable messages.
"""


class SogonError(Exception):
    """Base exception for all sogon errors."""
    pass


class TranscriptionError(SogonError):
    """Base exception for transcription-related errors."""
    pass


class ConfigurationError(SogonError):
    """
    Configuration validation error.

    Raised when configuration is invalid or incomplete.

    Attributes:
        message: Description of configuration issue
        field: Optional field name that caused error
    """

    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message)


class ProviderNotAvailableError(TranscriptionError):
    """
    Provider dependencies not available.

    Raised when transcription provider cannot be used due to missing
    dependencies or system requirements.

    Attributes:
        provider: Provider name
        missing_dependencies: List of missing packages
    """

    def __init__(self, provider: str, missing_dependencies: list[str] = None):
        self.provider = provider
        self.missing_dependencies = missing_dependencies or []

        if missing_dependencies:
            deps_str = ", ".join(missing_dependencies)
            message = (
                f"Provider '{provider}' not available. "
                f"Missing dependencies: {deps_str}. "
                f"Install with: pip install sogon[{provider}]"
            )
        else:
            message = (
                f"Provider '{provider}' not available. "
                f"Check system requirements and dependencies."
            )

        super().__init__(message)


class DeviceNotAvailableError(TranscriptionError):
    """
    Requested compute device not available.

    Raised when GPU/MPS device requested but not present.

    Attributes:
        device: Requested device name
        available_devices: List of available alternatives
    """

    def __init__(self, device: str, available_devices: list[str] = None):
        self.device = device
        self.available_devices = available_devices or ["cpu"]

        available_str = ", ".join(self.available_devices)
        message = (
            f"Device '{device}' not available. "
            f"Available devices: {available_str}. "
            f"Consider using CPU as fallback."
        )

        super().__init__(message)


class ResourceExhaustedError(TranscriptionError):
    """
    Insufficient system resources (RAM/VRAM/disk).

    Raised when resource requirements exceed available capacity.

    Attributes:
        resource_type: Type of resource (RAM/VRAM/disk)
        required: Required amount
        available: Available amount
        unit: Unit of measurement (GB/MB)
    """

    def __init__(
        self,
        resource_type: str,
        required: float,
        available: float,
        unit: str = "GB",
        suggestion: str = None,
    ):
        self.resource_type = resource_type
        self.required = required
        self.available = available
        self.unit = unit

        message = (
            f"Insufficient {resource_type}: requires {required:.1f}{unit}, "
            f"only {available:.1f}{unit} available."
        )

        if suggestion:
            message += f" {suggestion}"
        else:
            # Default suggestions based on resource type
            if resource_type == "RAM":
                message += " Close other applications or try a smaller model (tiny, base, small)."
            elif resource_type == "VRAM":
                message += " Use smaller model or switch to CPU device."
            elif resource_type == "disk":
                message += " Free up disk space or use a smaller model."

        super().__init__(message)


class InsufficientDiskSpaceError(ResourceExhaustedError):
    """
    Insufficient disk space for model download.

    Specialized ResourceExhaustedError for disk space issues (FR-005).
    """

    def __init__(self, required_gb: float, available_gb: float, model_name: str = None):
        suggestion = None
        if model_name:
            suggestion = f"Free up disk space or use a smaller model than '{model_name}'."

        super().__init__(
            resource_type="disk",
            required=required_gb,
            available=available_gb,
            unit="GB",
            suggestion=suggestion,
        )


class ModelCorruptionError(TranscriptionError):
    """
    Model file corrupted or checksum mismatch.

    Raised when downloaded model fails integrity verification (FR-003).

    Attributes:
        model_name: Name of corrupted model
        checksum_expected: Expected checksum (if available)
        checksum_actual: Actual calculated checksum
    """

    def __init__(
        self,
        model_name: str,
        checksum_expected: str = None,
        checksum_actual: str = None,
    ):
        self.model_name = model_name
        self.checksum_expected = checksum_expected
        self.checksum_actual = checksum_actual

        message = f"Model '{model_name}' appears corrupted."

        if checksum_expected and checksum_actual:
            message += (
                f" Checksum mismatch: expected {checksum_expected[:8]}..., "
                f"got {checksum_actual[:8]}..."
            )

        message += (
            " Delete cached model and retry download. "
            f"Check network connection or try different model."
        )

        super().__init__(message)


class AudioProcessingError(TranscriptionError):
    """
    Audio file processing error.

    Raised when audio file cannot be read or processed.

    Attributes:
        audio_path: Path to problematic audio file
        reason: Description of the issue
    """

    def __init__(self, audio_path: str, reason: str = None):
        self.audio_path = audio_path
        self.reason = reason

        message = f"Cannot process audio file: {audio_path}"

        if reason:
            message += f". {reason}"

        message += (
            " Verify file exists, is readable, and in supported format "
            "(mp3, wav, m4a, flac, ogg)."
        )

        super().__init__(message)


class ConcurrencyLimitError(TranscriptionError):
    """
    Maximum concurrent operations exceeded.

    Raised when trying to exceed max_workers limit (FR-022).

    Attributes:
        current: Current number of operations
        max_allowed: Maximum allowed concurrent operations
    """

    def __init__(self, current: int, max_allowed: int):
        self.current = current
        self.max_allowed = max_allowed

        message = (
            f"Concurrency limit reached: {current} operations active, "
            f"maximum {max_allowed} allowed. "
            f"Wait for operations to complete or increase max_workers setting."
        )

        super().__init__(message)
