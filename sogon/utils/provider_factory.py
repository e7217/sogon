"""
Provider factory for creating transcription providers based on configuration.

This module provides a centralized factory for creating transcription providers,
used by both CLI and API to ensure consistent provider instantiation.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_transcription_provider(settings):
    """
    Get transcription provider based on settings.

    Args:
        settings: Settings object containing provider configuration

    Returns:
        TranscriptionProvider instance or None for legacy API-based providers

    Raises:
        ProviderNotAvailableError: When provider dependencies are missing
        ValueError: When provider name is unknown
    """
    provider_name = settings.transcription_provider

    # Legacy API-based providers (OpenAI, Groq) - return None to use existing flow
    if provider_name in ["openai", "groq"]:
        logger.info(f"Using API-based provider: {provider_name}")
        return None

    # Local model provider (stable-whisper)
    if provider_name == "stable-whisper":
        # Lazy import to avoid circular dependency
        from sogon.providers.local.stable_whisper_provider import StableWhisperProvider
        from sogon.exceptions import ProviderNotAvailableError

        # Create provider instance
        local_config = settings.get_local_model_config()
        provider = StableWhisperProvider(local_config)

        # Check availability
        if not provider.is_available:
            deps = provider.get_required_dependencies()
            raise ProviderNotAvailableError(
                provider=provider_name,
                missing_dependencies=deps
            )

        logger.info(f"Created local provider: {provider.provider_name}")
        return provider

    # Unknown provider
    raise ValueError(f"Unknown transcription provider: {provider_name}")
