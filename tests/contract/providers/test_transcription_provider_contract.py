"""
Contract tests for TranscriptionProvider interface.

Ensures all transcription providers (OpenAI, Groq, FasterWhisper) implement
the TranscriptionProvider ABC correctly and produce consistent output formats.
"""

import pytest
from abc import ABC
from typing import Type
from unittest.mock import Mock, AsyncMock, patch

# Import will be available after Task 6 implementation
# from sogon.providers.base import TranscriptionProvider
# from sogon.providers.local.faster_whisper_provider import FasterWhisperProvider


@pytest.mark.skip("Task 6: TranscriptionProvider ABC not implemented yet")
class TestTranscriptionProviderInterface:
    """Test that all providers implement the TranscriptionProvider interface correctly."""

    def test_provider_implements_interface(self):
        """Verify all providers inherit from TranscriptionProvider ABC."""
        # This test will be implemented after Task 6
        # from sogon.providers.base import TranscriptionProvider
        # from sogon.providers.local.faster_whisper_provider import FasterWhisperProvider
        #
        # # Check FasterWhisperProvider inherits TranscriptionProvider
        # assert issubclass(FasterWhisperProvider, TranscriptionProvider)
        # assert issubclass(FasterWhisperProvider, ABC)
        #
        # # Verify all abstract methods are implemented
        # assert hasattr(FasterWhisperProvider, 'provider_name')
        # assert hasattr(FasterWhisperProvider, 'is_available')
        # assert hasattr(FasterWhisperProvider, 'transcribe')
        # assert hasattr(FasterWhisperProvider, 'validate_config')
        # assert hasattr(FasterWhisperProvider, 'get_required_dependencies')
        # assert hasattr(FasterWhisperProvider, 'transcribe_stream')
        pass

    @pytest.mark.asyncio
    async def test_provider_output_format_consistency(self):
        """
        All providers must return identical TranscriptionResult schema (FR-011).

        Test transcribes same mock audio with all providers and verifies:
        - Identical TranscriptionResult structure
        - Consistent timestamp formats (FR-012)
        """
        # This test will be implemented after Task 19
        # from sogon.providers.local.faster_whisper_provider import FasterWhisperProvider
        # from sogon.models.transcription import TranscriptionConfig, TranscriptionResult
        # from tests.fixtures.audio import SAMPLE_AUDIO_5SEC
        #
        # # Create configs for different providers
        # config_local = TranscriptionConfig(
        #     provider="faster-whisper",
        #     local=LocalModelConfiguration(model_name="tiny", device="cpu")
        # )
        #
        # # Mock providers
        # local_provider = FasterWhisperProvider(config_local.local)
        #
        # with patch.object(local_provider, 'transcribe', new_callable=AsyncMock) as mock_transcribe:
        #     mock_result = TranscriptionResult(
        #         text="Test transcription",
        #         segments=[{"start": 0.0, "end": 1.0, "text": "Test"}],
        #         language="en"
        #     )
        #     mock_transcribe.return_value = mock_result
        #
        #     result = await local_provider.transcribe(SAMPLE_AUDIO_5SEC, config_local)
        #
        #     # Verify result structure
        #     assert hasattr(result, 'text')
        #     assert hasattr(result, 'segments')
        #     assert hasattr(result, 'language')
        #
        #     # Verify timestamp format
        #     for segment in result.segments:
        #         assert 'start' in segment
        #         assert 'end' in segment
        #         assert isinstance(segment['start'], (int, float))
        #         assert isinstance(segment['end'], (int, float))
        pass

    def test_provider_error_handling(self):
        """
        Verify provider error handling includes actionable info (FR-025, FR-009).

        Each error condition should:
        - Raise appropriate error subclass
        - Include clear description
        - Provide actionable resolution steps
        """
        # This test will be implemented after Task 20 (error classes)
        # from sogon.exceptions import (
        #     ProviderNotAvailableError,
        #     DeviceNotAvailableError,
        #     ResourceExhaustedError,
        # )
        # from sogon.providers.local.faster_whisper_provider import FasterWhisperProvider
        #
        # # Test ProviderNotAvailableError
        # with patch('sogon.providers.local.faster_whisper_provider.importlib.import_module') as mock_import:
        #     mock_import.side_effect = ImportError("No module named 'faster_whisper'")
        #
        #     provider = FasterWhisperProvider(Mock())
        #     assert not provider.is_available
        #
        #     with pytest.raises(ProviderNotAvailableError) as exc_info:
        #         await provider.transcribe(Mock(), Mock())
        #
        #     error_msg = str(exc_info.value)
        #     assert "faster-whisper" in error_msg.lower()
        #     assert "install" in error_msg.lower()  # Actionable resolution
        pass

    def test_provider_availability_check(self):
        """
        Verify is_available returns False when dependencies missing.

        When dependencies are missing:
        - is_available should return False
        - transcribe() should raise ProviderNotAvailableError
        """
        # This test will be implemented after Task 19
        # from sogon.providers.local.faster_whisper_provider import FasterWhisperProvider
        # from sogon.exceptions import ProviderNotAvailableError
        #
        # with patch('sogon.providers.local.faster_whisper_provider.importlib.import_module') as mock_import:
        #     mock_import.side_effect = ImportError("No module named 'faster_whisper'")
        #
        #     config = Mock()
        #     provider = FasterWhisperProvider(config)
        #
        #     # Check availability
        #     assert provider.is_available is False
        #
        #     # Verify transcribe raises appropriate error
        #     with pytest.raises(ProviderNotAvailableError):
        #         await provider.transcribe(Mock(), Mock())
        pass

    def test_provider_config_validation(self):
        """
        Verify validate_config() raises clear errors for invalid configs.

        Invalid configurations should:
        - Raise ConfigurationError
        - Include specific validation failure reason
        - Provide guidance on correct values
        """
        # This test will be implemented after Task 19
        # from sogon.providers.local.faster_whisper_provider import FasterWhisperProvider
        # from sogon.exceptions import ConfigurationError
        # from sogon.models.transcription import TranscriptionConfig
        #
        # provider = FasterWhisperProvider(Mock())
        #
        # # Test: local config missing when provider is faster-whisper
        # invalid_config = TranscriptionConfig(
        #     provider="faster-whisper",
        #     local=None  # Missing required local config
        # )
        #
        # with pytest.raises(ConfigurationError) as exc_info:
        #     provider.validate_config(invalid_config)
        #
        # error_msg = str(exc_info.value)
        # assert "local" in error_msg.lower()
        # assert "required" in error_msg.lower()
        pass


@pytest.mark.skip("Task 19: FasterWhisperProvider not implemented yet")
class TestFasterWhisperProviderContractCompliance:
    """Test FasterWhisperProvider specific contract compliance."""

    def test_provider_name_is_faster_whisper(self):
        """Verify provider_name property returns 'faster-whisper'."""
        # from sogon.providers.local.faster_whisper_provider import FasterWhisperProvider
        #
        # provider = FasterWhisperProvider(Mock())
        # assert provider.provider_name == "faster-whisper"
        pass

    def test_get_required_dependencies_returns_correct_list(self):
        """Verify get_required_dependencies returns all required packages."""
        # from sogon.providers.local.faster_whisper_provider import FasterWhisperProvider
        #
        # provider = FasterWhisperProvider(Mock())
        # deps = provider.get_required_dependencies()
        #
        # assert "faster-whisper" in deps
        # assert "torch" in deps
        # assert "huggingface-hub" in deps
        # assert "psutil" in deps
        pass

    @pytest.mark.asyncio
    async def test_transcribe_returns_transcription_result(self):
        """Verify transcribe() returns valid TranscriptionResult."""
        # from sogon.providers.local.faster_whisper_provider import FasterWhisperProvider
        # from sogon.models.transcription import TranscriptionResult
        # from tests.fixtures.audio import SAMPLE_AUDIO_5SEC
        # from tests.fixtures.configs import VALID_CONFIG_CPU_TINY
        #
        # config = Mock()
        # config.local = Mock(**VALID_CONFIG_CPU_TINY)
        #
        # provider = FasterWhisperProvider(config.local)
        #
        # with patch.object(provider, '_load_model'), \
        #      patch.object(provider, '_transcribe_audio') as mock_transcribe:
        #     mock_transcribe.return_value = TranscriptionResult(
        #         text="Mock transcription",
        #         segments=[],
        #         language="en"
        #     )
        #
        #     result = await provider.transcribe(SAMPLE_AUDIO_5SEC, config)
        #
        #     assert isinstance(result, TranscriptionResult)
        #     assert hasattr(result, 'text')
        #     assert hasattr(result, 'segments')
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
