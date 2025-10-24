"""
TranscriptionProvider Abstract Base Class.

Defines the interface contract that all transcription providers must implement,
ensuring consistent output format and behavior across different backends.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator
from pathlib import Path

# These imports will be available from existing sogon models
# from sogon.models.audio import AudioFile
# from sogon.models.transcription import TranscriptionResult, TranscriptionConfig


class TranscriptionProvider(ABC):
    """
    Abstract base class for all transcription implementations.

    This interface ensures all providers (OpenAI, Groq, StableWhisper) produce
    identical output formats and implement consistent error handling.

    Invariants:
    - provider_name must be unique across all implementations
    - is_available must be checked before calling transcribe()
    - transcribe() must return consistent TranscriptionResult format
    - All methods must handle errors gracefully with clear messages (FR-009, FR-025)

    Example:
        >>> class MyProvider(TranscriptionProvider):
        ...     @property
        ...     def provider_name(self) -> str:
        ...         return "my-provider"
        ...
        ...     @property
        ...     def is_available(self) -> bool:
        ...         return True
        ...
        ...     async def transcribe(self, audio_file, config):
        ...         # Implementation here
        ...         pass
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Unique identifier for this provider.

        Returns:
            str: Provider name (e.g., "openai", "groq", "stable-whisper")

        Example:
            >>> provider = StableWhisperProvider(config)
            >>> provider.provider_name
            'stable-whisper'
        """
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider can be used (dependencies met, device available).

        Returns:
            bool: True if provider is ready to transcribe, False otherwise

        Example:
            >>> provider = StableWhisperProvider(config)
            >>> if provider.is_available:
            ...     result = await provider.transcribe(audio_file, config)
            ... else:
            ...     print(f"Provider not available: {provider.get_required_dependencies()}")
        """
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_file,  # AudioFile type hint will be added when importing from sogon.models
        config,      # TranscriptionConfig type hint
    ):  # -> TranscriptionResult
        """
        Transcribe audio file using provider-specific implementation.

        Args:
            audio_file: Audio file to transcribe
            config: Transcription configuration (provider-agnostic + provider-specific)

        Returns:
            TranscriptionResult: Transcription with text, segments, and metadata

        Raises:
            TranscriptionError: Base exception for all transcription failures
            ProviderNotAvailableError: Provider dependencies not met
            DeviceNotAvailableError: Requested device (GPU) not available
            ResourceExhaustedError: Insufficient memory (RAM/VRAM)
            ConfigurationError: Invalid configuration settings

        Example:
            >>> config = TranscriptionConfig(
            ...     provider="stable-whisper",
            ...     model="base",
            ...     language="en"
            ... )
            >>> result = await provider.transcribe(audio_file, config)
            >>> print(result.text)
            "Hello world"
        """
        pass

    @abstractmethod
    def validate_config(self, config) -> None:  # config: TranscriptionConfig
        """
        Validate provider-specific configuration.

        Args:
            config: Transcription configuration to validate

        Raises:
            ConfigurationError: If configuration is invalid with specific reason

        Example:
            >>> config = TranscriptionConfig(provider="stable-whisper")
            >>> provider.validate_config(config)  # Raises if local config missing
            ConfigurationError: local config required when provider='stable-whisper'
        """
        pass

    @abstractmethod
    def get_required_dependencies(self) -> list[str]:
        """
        Return list of required package names for this provider.

        Returns:
            list[str]: Package names that must be installed

        Example:
            >>> provider = StableWhisperProvider(config)
            >>> provider.get_required_dependencies()
            ['stable-ts', 'torch', 'huggingface-hub', 'psutil']
        """
        pass

    @abstractmethod
    async def transcribe_stream(
        self,
        audio_file,  # AudioFile
        config,      # TranscriptionConfig
    ) -> AsyncIterator[dict]:
        """
        Stream transcription segments as they become available.

        Args:
            audio_file: Audio file to transcribe
            config: Transcription configuration

        Yields:
            dict: Partial transcription segments with timing information

        Example:
            >>> async for segment in provider.transcribe_stream(audio, config):
            ...     print(f"[{segment['start']:.2f}s]: {segment['text']}")
            [0.00s]: Hello
            [1.50s]: world
        """
        pass
