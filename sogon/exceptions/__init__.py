"""
Custom exception hierarchy for SOGON
"""

from .base import SogonError, SogonConfigurationError, SogonValidationError
from .audio import (
    AudioError,
    AudioDownloadError,
    AudioProcessingError,
    AudioSplittingError,
    UnsupportedAudioFormatError,
    AudioFileNotFoundError,
    AudioCorruptedError
)
from .transcription import (
    TranscriptionError,
    TranscriptionAPIError,
    TranscriptionTimeoutError,
    TranscriptionModelError,
    TranscriptionQuotaError
)
from .job import (
    JobError,
    JobNotFoundError,
    JobCancelledError,
    JobTimeoutError,
    JobValidationError
)
from .local_model import (
    ProviderNotAvailableError,
    DeviceNotAvailableError,
    InsufficientDiskSpaceError,
    ResourceExhaustedError,
    ModelDownloadError,
    ModelCorruptionError,
    ConfigurationError
)

__all__ = [
    # Base exceptions
    "SogonError",
    "SogonConfigurationError", 
    "SogonValidationError",
    
    # Audio exceptions
    "AudioError",
    "AudioDownloadError",
    "AudioProcessingError",
    "AudioSplittingError",
    "UnsupportedAudioFormatError",
    "AudioFileNotFoundError",
    "AudioCorruptedError",
    
    # Transcription exceptions
    "TranscriptionError",
    "TranscriptionAPIError",
    "TranscriptionTimeoutError",
    "TranscriptionModelError",
    "TranscriptionQuotaError",

    # Job exceptions
    "JobError",
    "JobNotFoundError",
    "JobCancelledError",
    "JobTimeoutError",
    "JobValidationError",

    # Local model exceptions
    "ProviderNotAvailableError",
    "DeviceNotAvailableError",
    "InsufficientDiskSpaceError",
    "ResourceExhaustedError",
    "ModelDownloadError",
    "ModelCorruptionError",
    "ConfigurationError"
]