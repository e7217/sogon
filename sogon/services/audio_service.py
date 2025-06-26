"""
Audio service implementation
"""

import asyncio
import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor

from .interfaces import AudioService
from ..models.audio import AudioFile, AudioChunk
from ..exceptions.audio import AudioProcessingError, UnsupportedAudioFormatError
from ..downloader import split_audio_by_size
from ..config import get_settings

logger = logging.getLogger(__name__)


class AudioServiceImpl(AudioService):
    """Implementation of AudioService interface"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.settings = get_settings()
    
    async def get_audio_info(self, file_path: Path) -> AudioFile:
        """Get audio file information"""
        try:
            if not file_path.exists():
                raise AudioProcessingError(f"Audio file not found: {file_path}")
            
            # Get basic file info
            stat = file_path.stat()
            size_bytes = stat.st_size
            
            # For now, we'll use simple heuristics for duration
            # In a full implementation, you'd use a library like librosa or ffprobe
            estimated_duration = self._estimate_duration(size_bytes)
            
            # Extract format from file extension
            format_ext = file_path.suffix.lstrip('.').lower()
            
            return AudioFile(
                path=file_path,
                duration_seconds=estimated_duration,
                size_bytes=size_bytes,
                format=format_ext
            )
            
        except Exception as e:
            logger.error(f"Failed to get audio info for {file_path}: {e}")
            raise AudioProcessingError(f"Failed to analyze audio file: {e}")
    
    async def split_audio(self, audio_file: AudioFile, max_size_mb: float) -> List[AudioChunk]:
        """Split audio file into chunks"""
        try:
            if not audio_file.needs_splitting(max_size_mb):
                # Create a single chunk representing the whole file
                chunk = AudioChunk(
                    path=audio_file.path,
                    parent_file=audio_file,
                    chunk_number=1,
                    total_chunks=1,
                    start_time_seconds=0.0,
                    duration_seconds=audio_file.duration_seconds,
                    size_bytes=audio_file.size_bytes
                )
                return [chunk]
            
            # Use existing splitting logic in thread executor
            loop = asyncio.get_event_loop()
            chunk_paths = await loop.run_in_executor(
                self.executor, 
                self._split_audio_sync, 
                str(audio_file.path),
                max_size_mb
            )
            
            # Convert to AudioChunk objects
            chunks = []
            total_chunks = len(chunk_paths)
            
            for i, chunk_path in enumerate(chunk_paths):
                chunk_file_path = Path(chunk_path)
                if chunk_file_path.exists():
                    chunk_stat = chunk_file_path.stat()
                    # Calculate start time and duration for this chunk
                    chunk_duration = audio_file.duration_seconds / total_chunks
                    start_time = i * chunk_duration
                    
                    chunk = AudioChunk(
                        path=chunk_file_path,
                        parent_file=audio_file,
                        chunk_number=i + 1,
                        total_chunks=total_chunks,
                        start_time_seconds=start_time,
                        duration_seconds=chunk_duration,
                        size_bytes=chunk_stat.st_size
                    )
                    chunks.append(chunk)
            
            logger.info(f"Split audio into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to split audio {audio_file.path}: {e}")
            raise AudioProcessingError(f"Failed to split audio file: {e}")
    
    async def validate_format(self, audio_file: AudioFile, supported_formats: List[str]) -> bool:
        """Validate if audio format is supported"""
        is_supported = audio_file.is_format_supported(supported_formats)
        if not is_supported:
            logger.warning(f"Unsupported audio format: {audio_file.format}")
        return is_supported
    
    async def cleanup_chunks(self, chunks: List[AudioChunk]) -> int:
        """Clean up temporary audio chunks"""
        cleaned_count = 0
        for chunk in chunks:
            try:
                if chunk.cleanup():
                    cleaned_count += 1
            except Exception as e:
                logger.warning(f"Failed to cleanup chunk {chunk.path}: {e}")
        
        logger.info(f"Cleaned up {cleaned_count}/{len(chunks)} chunks")
        return cleaned_count
    
    def _estimate_duration(self, size_bytes: int) -> float:
        """Estimate audio duration based on file size (rough approximation)"""
        # Very rough estimate: assume 128kbps average bitrate
        # This is just a placeholder - real implementation would use audio analysis
        estimated_bitrate_bps = 128 * 1024  # 128 kbps in bits per second
        estimated_duration = (size_bytes * 8) / estimated_bitrate_bps
        return max(1.0, estimated_duration)  # At least 1 second
    
    def _split_audio_sync(self, audio_path: str, max_size_mb: float) -> List[tuple]:
        """Synchronous audio splitting wrapper"""
        try:
            # Use existing splitting function
            chunks_info = split_audio_by_size(audio_path, max_size_mb)
            return chunks_info
        except Exception as e:
            logger.error(f"Synchronous audio splitting failed: {e}")
            return []
    
    async def extract_audio_from_video(self, video_path: Path, output_dir: Optional[Path] = None) -> Path:
        """Extract audio from video file using FFmpeg"""
        try:
            if not video_path.exists():
                raise AudioProcessingError(f"Video file not found: {video_path}")
            
            # Determine output directory
            if output_dir is None:
                output_dir = Path(tempfile.mkdtemp())
            
            # Generate output audio file path
            audio_filename = f"{video_path.stem}_extracted.m4a"
            audio_path = output_dir / audio_filename
            
            # FFmpeg command to extract audio
            cmd = [
                "ffmpeg", "-y",  # -y to overwrite output files
                "-i", str(video_path),  # Input video file
                "-vn",  # Disable video
                "-acodec", "aac",  # Use AAC codec for compatibility
                "-ab", self.settings.audio_quality,  # Audio bitrate from settings
                "-ac", "1",  # Convert to mono (1 channel)
                "-map", "0:a?",  # Map first audio stream if exists (? makes it optional)
                str(audio_path)  # Output audio file
            ]
            
            # Run extraction in thread executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._run_ffmpeg_command,
                cmd
            )
            
            if not audio_path.exists():
                raise AudioProcessingError(f"Audio extraction failed - output file not created: {audio_path}")
            
            logger.info(f"Successfully extracted audio from {video_path} to {audio_path}")
            return audio_path
            
        except Exception as e:
            logger.error(f"Failed to extract audio from video {video_path}: {e}")
            raise AudioProcessingError(f"Video to audio extraction failed: {e}")
    
    def _run_ffmpeg_command(self, cmd: List[str]) -> None:
        """Run FFmpeg command synchronously"""
        try:
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            subprocess.run(
                cmd,
                check=True,
                capture_output=False,  # Don't capture output to see progress
                text=True,
                timeout=1800  # 30 minute timeout for large files
            )
            logger.info("FFmpeg command succeeded")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg command failed with return code {e.returncode}")
            raise AudioProcessingError(f"FFmpeg extraction failed: return code {e.returncode}")
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg command timed out (30 minutes)")
            raise AudioProcessingError("Video processing timed out")
    
    def __del__(self):
        """Cleanup executor on deletion"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)