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
from .correction import (
    CorrectionError,
    CorrectionAPIError,
    CorrectionTimeoutError
)
from .job import (
    JobError,
    JobNotFoundError,
    JobCancelledError,
    JobTimeoutError,
    JobValidationError
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
    
    # Correction exceptions
    "CorrectionError",
    "CorrectionAPIError",
    "CorrectionTimeoutError",
    
    # Job exceptions
    "JobError",
    "JobNotFoundError",
    "JobCancelledError",
    "JobTimeoutError",
    "JobValidationError"
]