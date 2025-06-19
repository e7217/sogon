"""
Audio File Manager - Handles audio file operations and cleanup
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AudioFileManager:
    """Manages audio file operations including cleanup and preservation"""
    
    def __init__(self, keep_audio: bool = False):
        """
        Initialize AudioFileManager
        
        Args:
            keep_audio (bool): Whether to keep audio files after processing
        """
        self.keep_audio = keep_audio
        self.temp_files = []  # Track temporary files for cleanup
        
    def handle_downloaded_audio(self, audio_path: str, output_dir: str, video_name: str) -> Optional[str]:
        """
        Handle downloaded audio file based on keep_audio setting
        
        Args:
            audio_path (str): Path to the downloaded audio file
            output_dir (str): Output directory for results
            video_name (str): Name for the final audio file
            
        Returns:
            Optional[str]: Final audio file path if kept, None if deleted
        """
        if self.keep_audio:
            return self._preserve_audio_file(audio_path, output_dir, video_name)
        else:
            self._cleanup_audio_file(audio_path)
            return None
    
    def _preserve_audio_file(self, audio_path: str, output_dir: str, video_name: str) -> Optional[str]:
        """
        Move audio file to output directory for preservation
        
        Args:
            audio_path (str): Source audio file path
            output_dir (str): Target output directory
            video_name (str): Base name for the audio file
            
        Returns:
            Optional[str]: Final audio file path if successful, None otherwise
        """
        try:
            audio_filename = f"{video_name}.mp3"
            final_audio_path = os.path.join(output_dir, audio_filename)
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Move the audio file
            shutil.move(audio_path, final_audio_path)
            logger.info(f"Audio file saved to: {final_audio_path}")
            
            # Clean up temporary directory if it's empty
            self._cleanup_temp_directory(audio_path)
            
            return final_audio_path
            
        except Exception as e:
            logger.warning(f"Failed to preserve audio file: {e}")
            # Fallback to cleanup on failure
            self._cleanup_audio_file(audio_path)
            return None
    
    def _cleanup_audio_file(self, audio_path: str) -> None:
        """
        Remove audio file and its temporary directory
        
        Args:
            audio_path (str): Path to audio file to remove
        """
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.debug(f"Audio file deleted: {audio_path}")
                
            self._cleanup_temp_directory(audio_path)
            
        except OSError as e:
            logger.warning(f"Failed to delete audio file {audio_path}: {e}")
    
    def _cleanup_temp_directory(self, file_path: str) -> None:
        """
        Clean up temporary directory if it's empty and was created by tempfile
        
        Args:
            file_path (str): Path to file within the temp directory
        """
        try:
            temp_dir = os.path.dirname(file_path)
            if temp_dir.startswith(tempfile.gettempdir()):
                # Only remove if directory is empty
                if not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
                    logger.debug(f"Temporary directory removed: {temp_dir}")
                    
        except OSError as e:
            logger.debug(f"Could not remove temporary directory: {e}")
    
    def add_temp_file(self, file_path: str) -> None:
        """
        Track a temporary file for later cleanup
        
        Args:
            file_path (str): Path to temporary file
        """
        self.temp_files.append(file_path)
    
    def cleanup_temp_files(self) -> None:
        """Clean up all tracked temporary files"""
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Temporary file cleaned up: {file_path}")
            except OSError as e:
                logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")
        
        self.temp_files.clear()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temp files"""
        self.cleanup_temp_files()


class AudioFileError(Exception):
    """Custom exception for audio file operations"""
    pass


class AudioFileNotFoundError(AudioFileError):
    """Raised when audio file is not found"""
    pass


class AudioFileOperationError(AudioFileError):
    """Raised when audio file operation fails"""
    pass