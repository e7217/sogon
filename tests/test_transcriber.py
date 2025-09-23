"""
Tests for transcriber module
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from sogon.transcriber import transcribe_audio, _convert_to_dict, _adjust_timestamps


class MockResponse:
    """Mock OpenAI response for testing"""
    def __init__(self, text="test", segments=None, words=None, language="en", duration=10.0):
        self.text = text
        self.segments = segments
        self.words = words
        self.language = language
        self.duration = duration


class TestTranscriberResponseHandling:
    """Test response handling edge cases"""

    @patch('sogon.transcriber.OpenAI')
    @patch('sogon.transcriber.split_audio_by_size')
    def test_none_segments_handling(self, mock_split, mock_openai):
        """Test handling when API returns segments=None"""
        # Setup
        mock_split.return_value = ["test_chunk.m4a"]
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Create response with None segments
        mock_response = MockResponse(text="test transcription", segments=None, words=None)
        mock_client.audio.transcriptions.create.return_value = mock_response

        # Mock file operations
        with patch('builtins.open', mock_open(read_data=b"fake audio data")):
            with patch('os.remove'):
                with patch('subprocess.run') as mock_subprocess:
                    mock_subprocess.return_value.stdout = '{"format": {"duration": "10.0"}}'

                    # Execute
                    result_text, result_metadata = transcribe_audio("test.m4a", api_key="test_key")

                    # Verify
                    assert result_text == "test transcription"
                    assert len(result_metadata) == 1
                    assert result_metadata[0]["segments"] == []
                    assert result_metadata[0]["words"] == []

    @patch('sogon.transcriber.OpenAI')
    @patch('sogon.transcriber.split_audio_by_size')
    def test_empty_list_segments_handling(self, mock_split, mock_openai):
        """Test handling when API returns segments=[]"""
        # Setup
        mock_split.return_value = ["test_chunk.m4a"]
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Create response with empty segments
        mock_response = MockResponse(text="test transcription", segments=[], words=[])
        mock_client.audio.transcriptions.create.return_value = mock_response

        # Mock file operations
        with patch('builtins.open', mock_open(read_data=b"fake audio data")):
            with patch('os.remove'):
                with patch('subprocess.run') as mock_subprocess:
                    mock_subprocess.return_value.stdout = '{"format": {"duration": "10.0"}}'

                    # Execute
                    result_text, result_metadata = transcribe_audio("test.m4a", api_key="test_key")

                    # Verify
                    assert result_text == "test transcription"
                    assert len(result_metadata) == 1
                    assert result_metadata[0]["segments"] == []
                    assert result_metadata[0]["words"] == []

    def test_convert_to_dict_with_none(self):
        """Test _convert_to_dict with None object"""
        result = _convert_to_dict(None)
        assert result == {}

    def test_convert_to_dict_with_dict(self):
        """Test _convert_to_dict with dict object"""
        test_dict = {"start": 1.0, "end": 2.0, "text": "hello"}
        result = _convert_to_dict(test_dict)
        assert result == test_dict

    def test_adjust_timestamps_with_none_attributes(self):
        """Test _adjust_timestamps when object has None timestamps"""
        adjusted_obj = {}
        original_obj = Mock()
        original_obj.start = None
        original_obj.end = None

        # Should not raise error
        _adjust_timestamps(adjusted_obj, original_obj, 5.0)

        # Should not add timestamp fields if original is None
        assert "start" not in adjusted_obj
        assert "end" not in adjusted_obj


class TestDebugScenarios:
    """Test scenarios for debugging response issues"""

    def test_inspect_response_structure(self):
        """Helper test to inspect actual OpenAI response structure"""
        # This test helps debug actual API response structure
        # Can be used with real API calls for debugging

        # Mock a realistic response structure
        mock_response = Mock()
        mock_response.text = "Sample transcription"
        mock_response.language = "ko"
        mock_response.duration = 15.5

        # Test different scenarios
        scenarios = [
            {"segments": None, "words": None, "description": "Both None"},
            {"segments": [], "words": [], "description": "Both empty"},
            {"segments": None, "words": [], "description": "Segments None, words empty"},
            {"segments": [], "words": None, "description": "Segments empty, words None"},
        ]

        for scenario in scenarios:
            mock_response.segments = scenario["segments"]
            mock_response.words = scenario["words"]

            # Test getattr behavior
            segments = getattr(mock_response, "segments", [])
            words = getattr(mock_response, "words", []) if hasattr(mock_response, "words") else []

            print(f"\n{scenario['description']}:")
            print(f"  segments: {segments} (type: {type(segments)})")
            print(f"  words: {words} (type: {type(words)})")
            print(f"  segments is None: {segments is None}")
            print(f"  words is None: {words is None}")

            # This should not raise error after fix
            try:
                list(segments) if segments is not None else []
                list(words) if words is not None else []
                print(f"  ✅ Iteration successful")
            except TypeError as e:
                print(f"  ❌ Iteration failed: {e}")


if __name__ == "__main__":
    # Run debug test to see response structure scenarios
    test_debug = TestDebugScenarios()
    test_debug.test_inspect_response_structure()