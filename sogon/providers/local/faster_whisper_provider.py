"""
FasterWhisperProvider: Local Whisper model transcription provider.

Implements TranscriptionProvider interface for faster-whisper backend.
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

# Imports will be available after Task 21
# from sogon.models.transcription import TranscriptionResult, TranscriptionSegment
# from sogon.models.transcription_config import TranscriptionConfig
# from sogon.models.audio import AudioFile

logger = logging.getLogger(__name__)


class FasterWhisperProvider(TranscriptionProvider):
    """
    Local transcription provider using faster-whisper.

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
        Initialize FasterWhisperProvider.

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
            f"Initialized FasterWhisperProvider: "
            f"model={config.model_name}, device={config.device}, "
            f"max_workers={config.max_workers}"
        )

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "faster-whisper"

    @property
    def is_available(self) -> bool:
        """
        Check if provider dependencies are available.

        Returns:
            True if all dependencies installed and device available
        """
        try:
            # Check required imports
            import faster_whisper
            import torch
            import huggingface_hub
            import psutil

            # Check device availability
            if not self._device_selector.is_device_available(self.config.device):
                logger.warning(
                    f"Device {self.config.device} not available for FasterWhisperProvider"
                )
                return False

            return True

        except ImportError as e:
            logger.warning(f"FasterWhisperProvider dependencies missing: {e}")
            return False

    def get_required_dependencies(self) -> list[str]:
        """Return list of required package names."""
        return [
            "faster-whisper",
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
        if config.provider == "faster-whisper" and not hasattr(config, 'local'):
            raise ConfigurationError(
                "local configuration required when provider='faster-whisper'. "
                "Provide LocalModelConfiguration.",
                field="local"
            )

        if not config.local:
            raise ConfigurationError(
                "local configuration missing for faster-whisper provider",
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
        Transcribe audio file using local Whisper model.

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

            # Transcribe with faster-whisper
            segments, info = await asyncio.to_thread(
                model.transcribe,
                str(audio_file.path),
                language=self.config.language,
                beam_size=self.config.beam_size,
                temperature=self.config.temperature,
                vad_filter=self.config.vad_filter,
            )

            # Convert segments to list
            segment_list = []
            full_text = []

            for segment in segments:
                segment_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                }
                segment_list.append(segment_dict)
                full_text.append(segment.text.strip())

            # Create TranscriptionResult
            # TODO: Replace with actual model when Task 21 complete
            result = type('TranscriptionResult', (), {
                'text': " ".join(full_text),
                'segments': segment_list,
                'language': info.language,
                'provider': self.provider_name,
                'duration': info.duration if hasattr(info, 'duration') else None,
            })()

            logger.info(
                f"Transcription complete: {len(segment_list)} segments, "
                f"language={info.language}"
            )

            return result

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

            # Stream transcription
            def transcribe_sync():
                return model.transcribe(
                    str(audio_file.path),
                    language=self.config.language,
                    beam_size=self.config.beam_size,
                    temperature=self.config.temperature,
                    vad_filter=self.config.vad_filter,
                )

            segments, info = await asyncio.to_thread(transcribe_sync)

            # Yield segments as they're generated
            for segment in segments:
                segment_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                }
                yield segment_dict

            logger.info(f"Streaming transcription complete")
