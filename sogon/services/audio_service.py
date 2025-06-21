"""
Audio service implementation
"""

import asyncio
import os
import logging
from pathlib import Path
from typing import List
from concurrent.futures import ThreadPoolExecutor

from .interfaces import AudioService
from ..models.audio import AudioFile, AudioChunk
from ..exceptions.audio import AudioProcessingError, UnsupportedAudioFormatError
from ..downloader import split_audio_by_size

logger = logging.getLogger(__name__)


class AudioServiceImpl(AudioService):
    """Implementation of AudioService interface"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
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
                str(audio_file.path)
            )
            
            # Convert to AudioChunk objects
            chunks = []
            total_chunks = len(chunk_paths)
            
            for i, (chunk_path, start_time) in enumerate(chunk_paths):
                chunk_file_path = Path(chunk_path)
                if chunk_file_path.exists():
                    chunk_stat = chunk_file_path.stat()
                    # Estimate chunk duration (simplified)
                    chunk_duration = audio_file.duration_seconds / total_chunks
                    
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
    
    def _split_audio_sync(self, audio_path: str) -> List[tuple]:
        """Synchronous audio splitting wrapper"""
        try:
            # Use existing splitting function
            chunks_info = split_audio_by_size(audio_path)
            return chunks_info
        except Exception as e:
            logger.error(f"Synchronous audio splitting failed: {e}")
            return []
    
    def __del__(self):
        """Cleanup executor on deletion"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)