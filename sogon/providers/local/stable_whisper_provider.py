"""
StableWhisperProvider: Local Whisper model transcription provider using stable-ts.

Implements TranscriptionProvider interface for stable-ts backend.
Provides improved timestamp accuracy and stability for subtitle generation.
"""

import asyncio
import logging
from typing import AsyncIterator
from pathlib import Path

from sogon.providers.base import TranscriptionProvider
from sogon.models.local_config import LocalModelConfiguration
from sogon.services.model_management.model_manager import ModelManager
from sogon.services.model_management.device_selector import DeviceSelector
from sogon.services.model_management.resource_monitor import ResourceMonitor
from sogon.services.model_management.model_key import ModelKey

from sogon.exceptions import (
    ConfigurationError,
    ProviderNotAvailableError,
    DeviceNotAvailableError,
    ResourceExhaustedError,
)

logger = logging.getLogger(__name__)


class StableWhisperProvider(TranscriptionProvider):
    """
    Local transcription provider using stable-ts for improved subtitle accuracy.

    stable-ts provides:
    - More accurate word-level timestamps
    - Silence suppression for better segment boundaries
    - VAD (Voice Activity Detection) filtering
    - Refinement algorithms for timestamp precision

    Implements:
    - Local model management with LRU caching
    - Device selection and validation
    - Resource monitoring and threshold enforcement
    - Concurrent transcription with semaphore limiting

    Configuration:
        Requires LocalModelConfiguration with:
        - model_name: Whisper model size
        - device: cpu/cuda/mps
        - compute_type: Precision (device-dependent)
        - max_workers: Concurrent job limit (FR-022)
    """

    def __init__(self, config: LocalModelConfiguration):
        """
        Initialize StableWhisperProvider.

        Args:
            config: Local model configuration
        """
        self.config = config
        self._model_manager = ModelManager(config)
        self._device_selector = DeviceSelector()
        self._resource_monitor = ResourceMonitor()

        # Concurrency control (FR-022)
        self._semaphore = asyncio.Semaphore(config.max_workers)

        logger.info(
            f"Initialized StableWhisperProvider: "
            f"model={config.model_name}, device={config.device}, "
            f"max_workers={config.max_workers}"
        )

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "stable-whisper"

    @property
    def is_available(self) -> bool:
        """
        Check if provider dependencies are available.

        Returns:
            True if all dependencies installed and device available
        """
        try:
            # Check required imports
            import stable_whisper
            import torch
            import huggingface_hub
            import psutil

            # Check device availability
            if not self._device_selector.is_device_available(self.config.device):
                logger.warning(
                    f"Device {self.config.device} not available for StableWhisperProvider"
                )
                return False

            return True

        except ImportError as e:
            logger.warning(f"StableWhisperProvider dependencies missing: {e}")
            return False

    def get_required_dependencies(self) -> list[str]:
        """Return list of required package names."""
        return [
            "stable-ts",
            "torch",
            "huggingface-hub",
            "psutil",
        ]

    def validate_config(self, config) -> None:  # config: TranscriptionConfig
        """
        Validate provider-specific configuration.

        Args:
            config: Transcription configuration

        Raises:
            ConfigurationError: When local config missing or invalid
            DeviceNotAvailableError: When device unavailable
        """
        # Check local config present
        if config.provider == "stable-whisper" and not hasattr(config, 'local'):
            raise ConfigurationError(
                "local configuration required when provider='stable-whisper'. "
                "Provide LocalModelConfiguration.",
                field="local"
            )

        if not config.local:
            raise ConfigurationError(
                "local configuration missing for stable-whisper provider",
                field="local"
            )

        # Validate device availability
        self._device_selector.raise_if_unavailable(config.local.device)

        # Validate device-compute_type compatibility
        self._device_selector.validate_device_compute_type(
            config.local.device,
            config.local.compute_type
        )

        logger.info(f"Configuration validated for {self.provider_name}")

    async def transcribe(
        self,
        audio_file,  # AudioFile
        config,      # TranscriptionConfig
    ):  # -> TranscriptionResult
        """
        Transcribe audio file using local Whisper model with stable-ts.

        Args:
            audio_file: Audio file to transcribe
            config: Transcription configuration

        Returns:
            TranscriptionResult with text, segments, metadata

        Raises:
            ResourceExhaustedError: Insufficient RAM/VRAM
            DeviceNotAvailableError: Device unavailable
        """
        async with self._semaphore:  # Limit concurrent jobs (FR-022)
            logger.info(
                f"Starting transcription: {audio_file.path}, "
                f"model={self.config.model_name}, device={self.config.device}"
            )

            # Validate resources before loading model (FR-021)
            required_ram_gb = self.config.get_min_ram_gb()
            required_vram_gb = self.config.get_min_vram_gb()

            self._resource_monitor.validate_resources_for_model(
                model_name=self.config.model_name,
                device=self.config.device,
                required_ram_gb=required_ram_gb,
                required_vram_gb=required_vram_gb,
            )

            # Get model (from cache or download)
            model_key = ModelKey(
                model_name=self.config.model_name,
                device=self.config.device,
                compute_type=self.config.compute_type,
            )

            model = await self._model_manager.get_model(model_key)

            # Transcribe with stable-whisper
            # stable-ts provides better timestamp accuracy for subtitles
            result = await asyncio.to_thread(
                model.transcribe,
                str(audio_file.path),
                language=self.config.language,
                beam_size=self.config.beam_size,
                temperature=self.config.temperature,
                # stable-ts specific parameters for better subtitle quality
                vad=self.config.vad_filter,  # stable-ts uses 'vad' parameter instead of 'vad_filter'
                suppress_silence=True,  # Adjust timestamps based on silence
                word_timestamps=True,   # Word-level timing
                regroup=True,          # Smart segment regrouping
            )

            # Convert stable-ts WhisperResult to our format
            segment_list = []
            full_text = []

            for segment in result.segments:
                segment_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                }
                segment_list.append(segment_dict)
                full_text.append(segment.text.strip())

            # Create TranscriptionResult
            # TODO: Replace with actual model when Task 21 complete
            transcription_result = type('TranscriptionResult', (), {
                'text': " ".join(full_text),
                'segments': segment_list,
                'language': result.language,
                'provider': self.provider_name,
                'duration': getattr(result, 'duration', None),
            })()

            logger.info(
                f"Transcription complete: {len(segment_list)} segments, "
                f"language={result.language}"
            )

            return transcription_result

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
            Dictionary with segment data (start, end, text)
        """
        async with self._semaphore:
            logger.info(f"Starting streaming transcription: {audio_file.path}")

            # Validate resources
            required_ram_gb = self.config.get_min_ram_gb()
            required_vram_gb = self.config.get_min_vram_gb()

            self._resource_monitor.validate_resources_for_model(
                model_name=self.config.model_name,
                device=self.config.device,
                required_ram_gb=required_ram_gb,
                required_vram_gb=required_vram_gb,
            )

            # Get model
            model_key = ModelKey(
                model_name=self.config.model_name,
                device=self.config.device,
                compute_type=self.config.compute_type,
            )

            model = await self._model_manager.get_model(model_key)

            # Stream transcription with stable-ts
            # Note: stream=True still returns WhisperResult, we yield segments afterward
            def transcribe_sync():
                return model.transcribe(
                    str(audio_file.path),
                    language=self.config.language,
                    beam_size=self.config.beam_size,
                    temperature=self.config.temperature,
                    vad=self.config.vad_filter,  # stable-ts uses 'vad' parameter instead of 'vad_filter'
                    suppress_silence=True,
                    word_timestamps=True,
                    regroup=True,
                    # stream=True,  # Enable streaming mode for better memory efficiency
                )

            result = await asyncio.to_thread(transcribe_sync)

            # Yield segments as they're generated
            for segment in result.segments:
                segment_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                }
                yield segment_dict

            logger.info(f"Streaming transcription complete")
