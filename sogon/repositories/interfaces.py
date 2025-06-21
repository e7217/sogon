"""
Repository interfaces for data access operations
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pathlib import Path

from ..models.job import ProcessingJob, JobStatus
from ..models.transcription import TranscriptionResult
from ..models.audio import AudioFile


class FileRepository(ABC):
    """Interface for file system operations"""
    
    @abstractmethod
    async def save_text_file(self, content: str, file_path: Path) -> bool:
        """Save text content to file"""
        pass
    
    @abstractmethod
    async def save_json_file(self, data: Dict[str, Any], file_path: Path) -> bool:
        """Save JSON data to file"""
        pass
    
    @abstractmethod
    async def read_text_file(self, file_path: Path) -> Optional[str]:
        """Read text content from file"""
        pass
    
    @abstractmethod
    async def read_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Read JSON data from file"""
        pass
    
    @abstractmethod
    async def create_directory(self, dir_path: Path) -> bool:
        """Create directory if it doesn't exist"""
        pass
    
    @abstractmethod
    async def file_exists(self, file_path: Path) -> bool:
        """Check if file exists"""
        pass
    
    @abstractmethod
    async def get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get file information (size, modified time, etc.)"""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: Path) -> bool:
        """Delete file"""
        pass


class JobRepository(ABC):
    """Interface for job persistence operations"""
    
    @abstractmethod
    async def save_job(self, job: ProcessingJob) -> bool:
        """Save processing job"""
        pass
    
    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Get processing job by ID"""
        pass
    
    @abstractmethod
    async def update_job_status(self, job_id: str, status: JobStatus) -> bool:
        """Update job status"""
        pass
    
    @abstractmethod
    async def get_jobs_by_status(self, status: JobStatus) -> List[ProcessingJob]:
        """Get jobs by status"""
        pass
    
    @abstractmethod
    async def delete_job(self, job_id: str) -> bool:
        """Delete job"""
        pass
    
    @abstractmethod
    async def cleanup_old_jobs(self, days: int = 7) -> int:
        """Clean up jobs older than specified days"""
        pass


class CacheRepository(ABC):
    """Interface for caching operations"""
    
    @abstractmethod
    async def get_transcription(self, audio_hash: str) -> Optional[TranscriptionResult]:
        """Get cached transcription result"""
        pass
    
    @abstractmethod
    async def save_transcription(self, audio_hash: str, result: TranscriptionResult) -> bool:
        """Save transcription result to cache"""
        pass
    
    @abstractmethod
    async def get_audio_info(self, file_path: str) -> Optional[AudioFile]:
        """Get cached audio file info"""
        pass
    
    @abstractmethod
    async def save_audio_info(self, file_path: str, audio_info: AudioFile) -> bool:
        """Save audio file info to cache"""
        pass
    
    @abstractmethod
    async def invalidate(self, key: str) -> bool:
        """Invalidate cache entry"""
        pass
    
    @abstractmethod
    async def clear_cache(self) -> bool:
        """Clear all cache entries"""
        pass
    
    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass