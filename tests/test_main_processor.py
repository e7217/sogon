"""
Tests for main_processor module
"""

import unittest
from unittest.mock import patch
from sogon.main_processor import is_url, process_input_to_subtitle


class TestMainProcessor(unittest.TestCase):
    """Test cases for main processor functionality"""

    def test_is_url_with_youtube_urls(self):
        """Test URL detection for various YouTube URL formats"""
        youtube_urls = [
            "https://www.youtube.com/watch?v=example",
            "http://youtube.com/watch?v=example",
            "https://youtu.be/example",
            "www.youtube.com/watch?v=example"
        ]
        
        for url in youtube_urls:
            with self.subTest(url=url):
                self.assertTrue(is_url(url))

    def test_is_url_with_file_paths(self):
        """Test URL detection returns False for file paths"""
        file_paths = [
            "/path/to/audio.wav",
            "./local/file.mp3",
            "audio_file.m4a",
            "C:\\Windows\\audio.wav"
        ]
        
        for path in file_paths:
            with self.subTest(path=path):
                self.assertFalse(is_url(path))

    def test_is_url_with_other_urls(self):
        """Test URL detection with non-YouTube URLs"""
        other_urls = [
            "https://example.com",
            "http://www.example.com",
            "www.example.com"
        ]
        
        for url in other_urls:
            with self.subTest(url=url):
                self.assertTrue(is_url(url))

    @patch('sogon.main_processor.youtube_to_subtitle')
    def test_process_input_with_url(self, mock_youtube_to_subtitle):
        """Test process_input_to_subtitle routes URLs to youtube_to_subtitle"""
        mock_youtube_to_subtitle.return_value = (["file1"], ["file2"], "output_dir")
        
        result = process_input_to_subtitle("https://youtube.com/watch?v=test")
        
        mock_youtube_to_subtitle.assert_called_once()
        self.assertEqual(result, (["file1"], ["file2"], "output_dir"))

    @patch('sogon.main_processor.file_to_subtitle')
    def test_process_input_with_file(self, mock_file_to_subtitle):
        """Test process_input_to_subtitle routes file paths to file_to_subtitle"""
        mock_file_to_subtitle.return_value = (["file1"], ["file2"], "output_dir")
        
        result = process_input_to_subtitle("/path/to/audio.wav")
        
        mock_file_to_subtitle.assert_called_once()
        self.assertEqual(result, (["file1"], ["file2"], "output_dir"))


if __name__ == '__main__':
    unittest.main()