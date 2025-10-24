"""
TranscriptionProvider Interface Contract

This file defines the abstract interface that ALL transcription providers must implement.
It serves as the contract for:
- OpenAIProvider (existing)
- GroqProvider (existing)
- FasterWhisperProvider (new - local models)

Contract ensures all providers produce identical output format (FR-011).
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator
from pathlib import Path

from sogon.models.audio import AudioFile
from sogon.models.transcription import TranscriptionResult, TranscriptionConfig


class TranscriptionProvider(ABC):
    """
    Abstract base class for all transcription implementations.

    Invariants:
    - provider_name must be unique across all implementations
    - is_available must be checked before calling transcribe()
    - transcribe() must return consistent TranscriptionResult format
    - All methods must handle errors gracefully with clear messages (FR-009, FR-025)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Unique identifier for this provider.

        Returns:
            str: Provider name (e.g., "openai", "groq", "faster-whisper")
        """
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider can be used (dependencies met, device available).

        Returns:
            bool: True if provider is ready to transcribe

        Example:
            >>> provider = FasterWhisperProvider(config)
            >>> if provider.is_available:
            ...     result = await provider.transcribe(audio)
        """
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_file: AudioFile,
        config: TranscriptionConfig,
    ) -> TranscriptionResult:
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
            ...     provider="faster-whisper",
            ...     model="base",
            ...     language="en"
            ... )
            >>> result = await provider.transcribe(audio_file, config)
            >>> print(result.text)
            "Hello world"
        """
        pass

    @abstractmethod
    def validate_config(self, config: TranscriptionConfig) -> None:
        """
        Validate provider-specific configuration.

        Args:
            config: Transcription configuration to validate

        Raises:
            ConfigurationError: If configuration is invalid with specific reason

        Example:
            >>> config = TranscriptionConfig(provider="faster-whisper")
            >>> provider.validate_config(config)  # Raises if local config missing
        """
        pass

    @abstractmethod
    def get_required_dependencies(self) -> list[str]:
        """
        Return list of required package names for this provider.

        Returns:
            list[str]: Package names that must be installed

        Example:
            >>> provider = FasterWhisperProvider(config)
            >>> provider.get_required_dependencies()
            ['faster-whisper', 'torch', 'huggingface-hub', 'psutil']
        """
        pass

    @abstractmethod
    async def transcribe_stream(
        self,
        audio_file: AudioFile,
        config: TranscriptionConfig,
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
        """
        pass


# Contract Tests (to be implemented in tests/contract/)
"""
Contract test requirements:

1. test_provider_implements_interface():
   - Verify all providers inherit from TranscriptionProvider
   - Verify all abstract methods implemented

2. test_provider_output_format_consistency():
   - Transcribe same audio with all providers
   - Assert identical TranscriptionResult schema (FR-011)
   - Assert timestamp formats match (FR-012)

3. test_provider_error_handling():
   - Trigger each error condition
   - Assert error messages include actionable info (FR-025, FR-009)
   - Assert error types are correct subclasses

4. test_provider_availability_check():
   - Mock missing dependencies
   - Assert is_available returns False
   - Assert transcribe() raises ProviderNotAvailableError

5. test_provider_config_validation():
   - Pass invalid configs
   - Assert validate_config() raises with clear messages
"""
