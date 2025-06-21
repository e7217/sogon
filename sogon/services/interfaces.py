"""
Service interfaces defining contracts for business logic operations
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from pathlib import Path

from ..models.audio import AudioFile, AudioChunk, AudioProcessingMetadata
from ..models.transcription import TranscriptionResult, TranscriptionSegment
from ..models.job import ProcessingJob, JobStatus
from ..models.correction import CorrectionResult


class AudioService(ABC):
    """Interface for audio processing operations"""
    
    @abstractmethod
    async def get_audio_info(self, file_path: Path) -> AudioFile:
        """Get audio file information"""
        pass
    
    @abstractmethod
    async def split_audio(self, audio_file: AudioFile, max_size_mb: float) -> List[AudioChunk]:
        """Split audio file into chunks"""
        pass
    
    @abstractmethod
    async def validate_format(self, audio_file: AudioFile, supported_formats: List[str]) -> bool:
        """Validate if audio format is supported"""
        pass
    
    @abstractmethod
    async def cleanup_chunks(self, chunks: List[AudioChunk]) -> int:
        """Clean up temporary audio chunks"""
        pass


class TranscriptionService(ABC):
    """Interface for audio transcription operations"""
    
    @abstractmethod
    async def transcribe_audio(self, audio_file: AudioFile) -> TranscriptionResult:
        """Transcribe single audio file"""
        pass
    
    @abstractmethod
    async def transcribe_chunks(self, chunks: List[AudioChunk]) -> List[TranscriptionResult]:
        """Transcribe multiple audio chunks"""
        pass
    
    @abstractmethod
    async def combine_transcriptions(self, results: List[TranscriptionResult]) -> TranscriptionResult:
        """Combine multiple transcription results"""
        pass


class CorrectionService(ABC):
    """Interface for text correction operations"""
    
    @abstractmethod
    async def correct_text(self, text: str, use_ai: bool = True) -> CorrectionResult:
        """Correct transcribed text"""
        pass
    
    @abstractmethod
    async def correct_transcription(self, transcription: TranscriptionResult, use_ai: bool = True) -> TranscriptionResult:
        """Correct transcription with metadata preservation"""
        pass


class YouTubeService(ABC):
    """Interface for YouTube operations"""
    
    @abstractmethod
    async def get_video_info(self, url: str) -> dict:
        """Get YouTube video information"""
        pass
    
    @abstractmethod
    async def download_audio(self, url: str, output_dir: Path) -> AudioFile:
        """Download audio from YouTube video"""
        pass
    
    @abstractmethod
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL"""
        pass


class FileService(ABC):
    """Interface for file operations"""
    
    @abstractmethod
    async def save_transcription(
        self, 
        transcription: TranscriptionResult, 
        output_dir: Path, 
        filename: str, 
        format: str = "txt"
    ) -> Path:
        """Save transcription to file"""
        pass
    
    @abstractmethod
    async def save_metadata(
        self, 
        metadata: dict, 
        output_dir: Path, 
        filename: str
    ) -> Path:
        """Save metadata to JSON file"""
        pass
    
    @abstractmethod
    async def save_timestamps(
        self, 
        transcription: TranscriptionResult, 
        output_dir: Path, 
        filename: str
    ) -> Path:
        """Save timestamped transcription"""
        pass
    
    @abstractmethod
    async def create_output_directory(self, base_dir: Path, video_title: Optional[str] = None) -> Path:
        """Create output directory with timestamp"""
        pass


class WorkflowService(ABC):
    """Interface for complete processing workflows"""
    
    @abstractmethod
    async def process_youtube_url(
        self,
        url: str,
        output_dir: Path,
        format: str = "txt",
        enable_correction: bool = True,
        use_ai_correction: bool = True,
        keep_audio: bool = False
    ) -> ProcessingJob:
        """Complete workflow for YouTube URL processing"""
        pass
    
    @abstractmethod
    async def process_local_file(
        self,
        file_path: Path,
        output_dir: Path,
        format: str = "txt", 
        enable_correction: bool = True,
        use_ai_correction: bool = True
    ) -> ProcessingJob:
        """Complete workflow for local file processing"""
        pass
    
    @abstractmethod
    async def get_job_status(self, job_id: str) -> JobStatus:
        """Get processing job status"""
        pass