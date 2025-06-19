"""
Tests for AudioFileManager
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from sogon.audio_manager import AudioFileManager, AudioFileError, AudioFileNotFoundError, AudioFileOperationError


class TestAudioFileManager(unittest.TestCase):
    """Test cases for AudioFileManager functionality"""

    def setUp(self):
        """Set up test environment"""
        self.test_temp_dir = tempfile.mkdtemp()
        self.test_output_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_temp_dir, ignore_errors=True)
        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_audio_manager_initialization(self):
        """Test AudioFileManager initialization"""
        # Test with keep_audio=False (default)
        manager = AudioFileManager()
        self.assertFalse(manager.keep_audio)
        self.assertEqual(manager.temp_files, [])
        
        # Test with keep_audio=True
        manager = AudioFileManager(keep_audio=True)
        self.assertTrue(manager.keep_audio)
        self.assertEqual(manager.temp_files, [])

    def test_handle_downloaded_audio_delete_mode(self):
        """Test audio handling in delete mode"""
        # Create a test audio file
        test_audio_path = os.path.join(self.test_temp_dir, "test_audio.mp3")
        with open(test_audio_path, 'w') as f:
            f.write("test audio content")
        
        manager = AudioFileManager(keep_audio=False)
        
        result = manager.handle_downloaded_audio(
            test_audio_path, self.test_output_dir, "test_video"
        )
        
        # Should return None in delete mode
        self.assertIsNone(result)
        # File should be deleted
        self.assertFalse(os.path.exists(test_audio_path))

    def test_handle_downloaded_audio_keep_mode(self):
        """Test audio handling in keep mode"""
        # Create a test audio file
        test_audio_path = os.path.join(self.test_temp_dir, "test_audio.mp3")
        with open(test_audio_path, 'w') as f:
            f.write("test audio content")
        
        manager = AudioFileManager(keep_audio=True)
        
        result = manager.handle_downloaded_audio(
            test_audio_path, self.test_output_dir, "test_video"
        )
        
        # Should return final path
        expected_path = os.path.join(self.test_output_dir, "test_video.mp3")
        self.assertEqual(result, expected_path)
        
        # File should exist at new location
        self.assertTrue(os.path.exists(expected_path))
        # Original file should be moved (not exist)
        self.assertFalse(os.path.exists(test_audio_path))
        
        # Check file content
        with open(expected_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "test audio content")

    def test_preserve_audio_file_creates_output_directory(self):
        """Test that preserve_audio_file creates output directory if it doesn't exist"""
        # Create a test audio file
        test_audio_path = os.path.join(self.test_temp_dir, "test_audio.mp3")
        with open(test_audio_path, 'w') as f:
            f.write("test audio content")
        
        # Use non-existent output directory
        non_existent_output_dir = os.path.join(self.test_output_dir, "subdir", "nested")
        
        manager = AudioFileManager(keep_audio=True)
        
        result = manager.handle_downloaded_audio(
            test_audio_path, non_existent_output_dir, "test_video"
        )
        
        # Should succeed and create directory
        expected_path = os.path.join(non_existent_output_dir, "test_video.mp3")
        self.assertEqual(result, expected_path)
        self.assertTrue(os.path.exists(expected_path))
        self.assertTrue(os.path.exists(non_existent_output_dir))

    @patch('sogon.audio_manager.shutil.move')
    def test_preserve_audio_file_failure_fallback(self, mock_move):
        """Test fallback behavior when preserve fails"""
        # Mock move to raise exception
        mock_move.side_effect = Exception("Move failed")
        
        # Create a test audio file
        test_audio_path = os.path.join(self.test_temp_dir, "test_audio.mp3")
        with open(test_audio_path, 'w') as f:
            f.write("test audio content")
        
        manager = AudioFileManager(keep_audio=True)
        
        result = manager.handle_downloaded_audio(
            test_audio_path, self.test_output_dir, "test_video"
        )
        
        # Should return None on failure
        self.assertIsNone(result)
        # Original file should be deleted as fallback
        self.assertFalse(os.path.exists(test_audio_path))

    def test_cleanup_temp_directory(self):
        """Test temporary directory cleanup"""
        # Create a temp file in system temp directory
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, "temp_audio.mp3")
        with open(temp_file, 'w') as f:
            f.write("temp content")
        
        manager = AudioFileManager()
        
        # Remove the file first
        os.remove(temp_file)
        
        # Then cleanup directory
        manager._cleanup_temp_directory(temp_file)
        
        # Directory should be removed
        self.assertFalse(os.path.exists(temp_dir))

    def test_cleanup_temp_directory_non_empty(self):
        """Test that non-empty temp directories are not removed"""
        # Create a temp directory with multiple files
        temp_dir = tempfile.mkdtemp()
        temp_file1 = os.path.join(temp_dir, "temp_audio1.mp3")
        temp_file2 = os.path.join(temp_dir, "temp_audio2.mp3")
        
        with open(temp_file1, 'w') as f:
            f.write("temp content 1")
        with open(temp_file2, 'w') as f:
            f.write("temp content 2")
        
        manager = AudioFileManager()
        
        # Try to cleanup directory (should not remove because it's not empty)
        manager._cleanup_temp_directory(temp_file1)
        
        # Directory should still exist
        self.assertTrue(os.path.exists(temp_dir))
        
        # Clean up manually
        import shutil
        shutil.rmtree(temp_dir)

    def test_add_temp_file_and_cleanup(self):
        """Test adding and cleaning up temporary files"""
        # Create test files
        temp_file1 = os.path.join(self.test_temp_dir, "temp1.mp3")
        temp_file2 = os.path.join(self.test_temp_dir, "temp2.mp3")
        
        with open(temp_file1, 'w') as f:
            f.write("temp content 1")
        with open(temp_file2, 'w') as f:
            f.write("temp content 2")
        
        manager = AudioFileManager()
        
        # Add files to track
        manager.add_temp_file(temp_file1)
        manager.add_temp_file(temp_file2)
        
        self.assertEqual(len(manager.temp_files), 2)
        
        # Cleanup
        manager.cleanup_temp_files()
        
        # Files should be deleted
        self.assertFalse(os.path.exists(temp_file1))
        self.assertFalse(os.path.exists(temp_file2))
        # Tracking list should be cleared
        self.assertEqual(len(manager.temp_files), 0)

    def test_context_manager(self):
        """Test AudioFileManager as context manager"""
        # Create test file
        temp_file = os.path.join(self.test_temp_dir, "temp.mp3")
        with open(temp_file, 'w') as f:
            f.write("temp content")
        
        # Use as context manager
        with AudioFileManager() as manager:
            manager.add_temp_file(temp_file)
            # File should exist during context
            self.assertTrue(os.path.exists(temp_file))
        
        # File should be cleaned up after context
        self.assertFalse(os.path.exists(temp_file))

    def test_cleanup_nonexistent_temp_files(self):
        """Test cleanup handles nonexistent files gracefully"""
        manager = AudioFileManager()
        
        # Add non-existent file
        manager.add_temp_file("/nonexistent/file.mp3")
        
        # Should not raise exception
        manager.cleanup_temp_files()
        
        # List should be cleared
        self.assertEqual(len(manager.temp_files), 0)

    def test_audio_file_exceptions(self):
        """Test custom exception classes"""
        # Test base exception
        with self.assertRaises(AudioFileError):
            raise AudioFileError("Test error")
        
        # Test specific exceptions
        with self.assertRaises(AudioFileNotFoundError):
            raise AudioFileNotFoundError("File not found")
        
        with self.assertRaises(AudioFileOperationError):
            raise AudioFileOperationError("Operation failed")
        
        # Test inheritance
        self.assertTrue(issubclass(AudioFileNotFoundError, AudioFileError))
        self.assertTrue(issubclass(AudioFileOperationError, AudioFileError))


if __name__ == '__main__':
    unittest.main()