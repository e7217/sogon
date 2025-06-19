"""
Audio-related domain models
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
from datetime import datetime


@dataclass
class AudioFile:
    """Represents an audio file with metadata"""
    
    path: Path
    duration_seconds: float
    size_bytes: int
    format: str
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    bitrate: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        
        # Ensure path is Path object
        if isinstance(self.path, str):
            self.path = Path(self.path)
    
    @property
    def size_mb(self) -> float:
        """File size in megabytes"""
        return self.size_bytes / (1024 * 1024)
    
    @property
    def duration_minutes(self) -> float:
        """Duration in minutes"""
        return self.duration_seconds / 60.0
    
    @property
    def name(self) -> str:
        """File name without path"""
        return self.path.name
    
    @property
    def stem(self) -> str:
        """File name without extension"""
        return self.path.stem
    
    @property
    def exists(self) -> bool:
        """Check if file exists"""
        return self.path.exists()
    
    def is_format_supported(self, supported_formats: List[str]) -> bool:
        """Check if audio format is supported"""
        return self.format.lower() in [fmt.lower() for fmt in supported_formats]
    
    def needs_splitting(self, max_size_mb: float) -> bool:
        """Check if file needs to be split based on size"""
        return self.size_mb > max_size_mb
    
    def estimate_chunks_needed(self, max_size_mb: float) -> int:
        """Estimate number of chunks needed for splitting"""
        if not self.needs_splitting(max_size_mb):
            return 1
        return int((self.size_mb / max_size_mb) + 0.5)
    
    def __str__(self) -> str:
        return f"AudioFile({self.name}, {self.size_mb:.1f}MB, {self.duration_minutes:.1f}min)"


@dataclass
class AudioChunk:
    """Represents a chunk of an audio file"""
    
    path: Path
    parent_file: AudioFile
    chunk_number: int
    total_chunks: int
    start_time_seconds: float
    duration_seconds: float
    size_bytes: int
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        
        # Ensure path is Path object
        if isinstance(self.path, str):
            self.path = Path(self.path)
    
    @property
    def size_mb(self) -> float:
        """Chunk size in megabytes"""
        return self.size_bytes / (1024 * 1024)
    
    @property
    def end_time_seconds(self) -> float:
        """End time in seconds"""
        return self.start_time_seconds + self.duration_seconds
    
    @property
    def start_time_minutes(self) -> float:
        """Start time in minutes"""
        return self.start_time_seconds / 60.0
    
    @property
    def duration_minutes(self) -> float:
        """Duration in minutes"""
        return self.duration_seconds / 60.0
    
    @property
    def name(self) -> str:
        """Chunk file name"""
        return self.path.name
    
    @property
    def exists(self) -> bool:
        """Check if chunk file exists"""
        return self.path.exists()
    
    @property
    def is_first_chunk(self) -> bool:
        """Check if this is the first chunk"""
        return self.chunk_number == 1
    
    @property
    def is_last_chunk(self) -> bool:
        """Check if this is the last chunk"""
        return self.chunk_number == self.total_chunks
    
    def cleanup(self) -> bool:
        """
        Remove chunk file from disk
        
        Returns:
            bool: True if successfully removed, False otherwise
        """
        try:
            if self.exists:
                self.path.unlink()
                return True
            return True  # Already doesn't exist
        except Exception:
            return False
    
    def __str__(self) -> str:
        return f"AudioChunk({self.chunk_number}/{self.total_chunks}, {self.size_mb:.1f}MB, {self.start_time_minutes:.1f}-{self.start_time_minutes + self.duration_minutes:.1f}min)"


@dataclass 
class AudioProcessingMetadata:
    """Metadata for audio processing operations"""
    
    original_file: AudioFile
    chunks: List[AudioChunk]
    processing_start: datetime
    processing_end: Optional[datetime] = None
    total_processing_time_seconds: Optional[float] = None
    
    @property
    def is_completed(self) -> bool:
        """Check if processing is completed"""
        return self.processing_end is not None
    
    @property
    def total_chunks(self) -> int:
        """Total number of chunks"""
        return len(self.chunks)
    
    @property
    def total_chunk_size_mb(self) -> float:
        """Total size of all chunks in MB"""
        return sum(chunk.size_mb for chunk in self.chunks)
    
    def mark_completed(self) -> None:
        """Mark processing as completed"""
        self.processing_end = datetime.now()
        self.total_processing_time_seconds = (
            self.processing_end - self.processing_start
        ).total_seconds()
    
    def cleanup_chunks(self) -> int:
        """
        Clean up all chunk files
        
        Returns:
            int: Number of successfully cleaned up chunks
        """
        cleaned = 0
        for chunk in self.chunks:
            if chunk.cleanup():
                cleaned += 1
        return cleaned
    
    def __str__(self) -> str:
        status = "completed" if self.is_completed else "in_progress"
        return f"AudioProcessingMetadata({self.original_file.name}, {self.total_chunks} chunks, {status})"