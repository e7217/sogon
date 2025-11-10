"""
SOGON Package
Package for extracting subtitles from YouTube videos or local audio files
"""

# New architecture (Phase 1 & Phase 2)
from .services import (
    AudioServiceImpl,
    TranscriptionServiceImpl,
    YouTubeServiceImpl,
    FileServiceImpl
)
from .config import get_settings

__version__ = "1.0.0"
__all__ = [
    "AudioServiceImpl",
    "TranscriptionServiceImpl",
    "YouTubeServiceImpl",
    "FileServiceImpl",
    "get_settings",
]
