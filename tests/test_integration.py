"""
Integration tests for SOGON file input functionality
"""

import unittest
from unittest.mock import patch
import tempfile
import os
from sogon.main_processor import file_to_subtitle


class TestFileIntegration(unittest.TestCase):
    """Integration tests for file-based subtitle generation"""

    def test_file_not_found(self):
        """Test handling of non-existent file"""
        result = file_to_subtitle("/non/existent/file.wav")
        self.assertEqual(result, (None, None, None))

    @patch('sogon.main_processor.transcribe_audio')
    @patch('sogon.main_processor.save_subtitle_and_metadata')
    @patch('sogon.main_processor.create_output_directory')
    def test_file_processing_workflow(self, mock_create_dir, mock_save, mock_transcribe):
        """Test the complete file processing workflow with mocks"""
        # Create a temporary file to simulate an audio file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_file.write(b'fake audio data')
            temp_path = tmp_file.name

        try:
            # Setup mocks
            mock_create_dir.return_value = "/fake/output/dir"
            mock_transcribe.return_value = ("Transcribed text", {"metadata": "fake"})
            mock_save.return_value = (
                "subtitle.txt", "metadata.json", "timestamps.txt", 
                ("corrected.txt", "corrected_meta.json", "corrected_timestamps.txt")
            )

            # Call the function
            result = file_to_subtitle(temp_path)

            # Verify the workflow
            mock_create_dir.assert_called_once()
            mock_transcribe.assert_called_once_with(temp_path)
            mock_save.assert_called_once()

            # Check return value structure
            original_files, corrected_files, output_dir = result
            self.assertEqual(len(original_files), 3)
            self.assertEqual(len(corrected_files), 3)
            self.assertEqual(output_dir, "/fake/output/dir")

        finally:
            # Clean up temporary file
            os.unlink(temp_path)


if __name__ == '__main__':
    unittest.main()