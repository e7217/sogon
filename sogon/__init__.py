"""
SOGON Package
Package for extracting and correcting subtitles from YouTube videos or local audio files
"""

from .downloader import download_youtube_audio
from .transcriber import transcribe_audio
from .corrector import correct_transcription_text, fix_ai_based_corrections
from .utils import create_output_directory, save_subtitle_and_metadata
from .main_processor import youtube_to_subtitle, file_to_subtitle, process_input_to_subtitle
from .audio_manager import AudioFileManager

__version__ = "1.0.0"
__all__ = [
    "download_youtube_audio",
    "transcribe_audio",
    "correct_transcription_text",
    "fix_ai_based_corrections",
    "create_output_directory",
    "save_subtitle_and_metadata",
    "youtube_to_subtitle",
    "file_to_subtitle",
    "process_input_to_subtitle",
    "AudioFileManager",
]
