"""
YouTube service implementation
"""

import os
import logging
import asyncio
from pathlib import Path
import yt_dlp
from .interfaces import YouTubeService
from ..models.audio import AudioFile

logger = logging.getLogger(__name__)

class YouTubeServiceImpl(YouTubeService):
    """Implementation of YouTubeService interface"""
    
    def __init__(self, timeout: int = 30, retries: int = 3, preferred_format: str = "m4a"):
        self.timeout = timeout
        self.retries = retries
        self.preferred_format = preferred_format
    
    async def get_video_info(self, url: str) -> dict:
        """Get YouTube video information"""
        def _get_info():
            ydl_opts = {
                'quiet': True,
                'no_warnings': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _get_info)
        return {
            "title": info.get("title", "unknown_video"),
            "duration": info.get("duration", 0)
        }
    
    async def download_audio(self, url: str, output_dir: Path) -> AudioFile:
        """Download audio from YouTube video"""
        def _download():
            ydl_opts = {
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "extractaudio": True,
                "audioformat": self.preferred_format,
                "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
                "socket_timeout": self.timeout,
                "retries": self.retries,
                "fragment_retries": self.retries,
                "http_chunk_size": 5242880,
                "concurrent_fragment_downloads": 4,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": self.preferred_format,
                        "preferredquality": "128",
                    }
                ],
                "quiet": True,
                "no_warnings": True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # yt-dlp changes extension after postprocessing
                audio_path = Path(filename).with_suffix(f'.{self.preferred_format}')
                
                if audio_path.exists():
                    return audio_path
                
                # Fallback: look for any audio file in output directory
                for file in output_dir.glob('*'):
                    if file.suffix.lower() in ['.m4a', '.mp3', '.wav', '.ogg']:
                        return file
                
                raise Exception(f"Downloaded audio file not found in {output_dir}")
        
        loop = asyncio.get_event_loop()
        audio_path = await loop.run_in_executor(None, _download)
        
        # Get file information
        stat = audio_path.stat()
        
        return AudioFile(
            path=audio_path,
            duration_seconds=0.0,  # Will be determined by audio service
            size_bytes=stat.st_size,
            format=audio_path.suffix[1:]  # Remove the dot
        )
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL"""
        return "youtube.com" in url or "youtu.be" in url