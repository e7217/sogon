"""
Job processing domain models
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class JobType(Enum):
    """Job type enumeration"""
    
    YOUTUBE_URL = "youtube_url"
    LOCAL_FILE = "local_file"


class JobStatus(Enum):
    """Job processing status enumeration"""
    
    PENDING = "pending"
    DOWNLOADING = "downloading"
    SPLITTING = "splitting"
    TRANSCRIBING = "transcribing"
    CORRECTING = "correcting"
    TRANSLATING = "translating"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NOT_FOUND = "not_found"
    
    @property
    def is_terminal(self) -> bool:
        """Check if status is terminal (won't change)"""
        return self in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
    
    @property
    def is_processing(self) -> bool:
        """Check if job is currently processing"""
        return self in {
            JobStatus.DOWNLOADING,
            JobStatus.SPLITTING, 
            JobStatus.TRANSCRIBING,
            JobStatus.CORRECTING,
            JobStatus.TRANSLATING,
            JobStatus.SAVING
        }


@dataclass
class JobProgress:
    """Progress information for a job"""
    
    current_step: str
    total_steps: int
    completed_steps: int
    current_step_progress: float = 0.0  # 0.0 to 1.0
    details: Optional[str] = None
    
    @property
    def overall_progress(self) -> float:
        """Calculate overall progress (0.0 to 1.0)"""
        if self.total_steps == 0:
            return 0.0
        
        step_progress = self.completed_steps / self.total_steps
        current_contribution = self.current_step_progress / self.total_steps
        return min(1.0, step_progress + current_contribution)
    
    @property
    def percentage(self) -> int:
        """Progress as percentage (0-100)"""
        return int(self.overall_progress * 100)
    
    def __str__(self) -> str:
        return f"{self.current_step} ({self.percentage}%)"


@dataclass
class ProcessingJob:
    """Represents a processing job with status and metadata"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_type: Optional[JobType] = None
    input_path: str = ""
    output_directory: Optional[str] = None
    actual_output_dir: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    progress: Optional[JobProgress] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Configuration
    subtitle_format: str = "txt"
    enable_correction: bool = True
    use_ai_correction: bool = True
    keep_audio: bool = False
    enable_translation: bool = False
    translation_target_language: Optional[str] = None
    whisper_source_language: Optional[str] = None  # None means auto-detect
    
    # Results
    original_files: Optional[Dict[str, str]] = None  # {type: path}
    corrected_files: Optional[Dict[str, str]] = None  # {type: path}
    translated_files: Optional[Dict[str, str]] = None  # {type: path}
    error_message: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """Job duration in seconds"""
        if self.started_at is None:
            return None
        
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    @property
    def is_terminal(self) -> bool:
        """Check if job is in terminal state"""
        return self.status.is_terminal
    
    @property
    def is_processing(self) -> bool:
        """Check if job is currently processing"""
        return self.status.is_processing
    
    @property
    def is_successful(self) -> bool:
        """Check if job completed successfully"""
        return self.status == JobStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if job failed"""
        return self.status == JobStatus.FAILED
    
    def start(self) -> None:
        """Mark job as started"""
        if self.started_at is None:
            self.started_at = datetime.now()
    
    def complete(
        self, 
        original_files: Dict[str, str], 
        corrected_files: Optional[Dict[str, str]] = None,
        translated_files: Optional[Dict[str, str]] = None
    ) -> None:
        """Mark job as completed with results"""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now()
        self.original_files = original_files
        self.corrected_files = corrected_files
        self.translated_files = translated_files
        self.error_message = None
    
    def fail(self, error_message: str) -> None:
        """Mark job as failed with error"""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error_message
    
    def cancel(self) -> None:
        """Mark job as cancelled"""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.now()
    
    def update_status(self, status: JobStatus, progress: Optional[JobProgress] = None) -> None:
        """Update job status and progress"""
        self.status = status
        if progress is not None:
            self.progress = progress
        
        # Start job if moving from pending
        if status != JobStatus.PENDING and self.started_at is None:
            self.start()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to job"""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value"""
        return self.metadata.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization"""
        return {
            "id": self.id,
            "input_path": self.input_path,
            "output_directory": self.output_directory,
            "status": self.status.value,
            "progress": {
                "current_step": self.progress.current_step,
                "total_steps": self.progress.total_steps,
                "completed_steps": self.progress.completed_steps,
                "current_step_progress": self.progress.current_step_progress,
                "overall_progress": self.progress.overall_progress,
                "percentage": self.progress.percentage,
                "details": self.progress.details
            } if self.progress else None,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "subtitle_format": self.subtitle_format,
            "enable_correction": self.enable_correction,
            "use_ai_correction": self.use_ai_correction,
            "keep_audio": self.keep_audio,
            "enable_translation": self.enable_translation,
            "translation_target_language": self.translation_target_language,
            "whisper_source_language": self.whisper_source_language,
            "original_files": self.original_files,
            "corrected_files": self.corrected_files,
            "translated_files": self.translated_files,
            "error_message": self.error_message,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingJob':
        """Create job from dictionary"""
        job = cls(
            id=data["id"],
            input_path=data["input_path"],
            output_directory=data.get("output_directory"),
            status=JobStatus(data["status"]),
            subtitle_format=data.get("subtitle_format", "txt"),
            enable_correction=data.get("enable_correction", True),
            use_ai_correction=data.get("use_ai_correction", True),
            keep_audio=data.get("keep_audio", False),
            enable_translation=data.get("enable_translation", False),
            translation_target_language=data.get("translation_target_language"),
            whisper_source_language=data.get("whisper_source_language"),
            original_files=data.get("original_files"),
            corrected_files=data.get("corrected_files"),
            translated_files=data.get("translated_files"),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {})
        )
        
        # Parse timestamps
        job.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            job.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            job.completed_at = datetime.fromisoformat(data["completed_at"])
        
        # Parse progress
        if data.get("progress"):
            progress_data = data["progress"]
            job.progress = JobProgress(
                current_step=progress_data["current_step"],
                total_steps=progress_data["total_steps"],
                completed_steps=progress_data["completed_steps"],
                current_step_progress=progress_data.get("current_step_progress", 0.0),
                details=progress_data.get("details")
            )
        
        return job
    
    def __str__(self) -> str:
        progress_str = f" ({self.progress.percentage}%)" if self.progress else ""
        return f"Job {self.id[:8]} [{self.status.value}{progress_str}]: {self.input_path}"


@dataclass
class JobResult:
    """Result of a completed job"""
    
    job_id: str
    success: bool
    original_files: Optional[Dict[str, str]] = None
    corrected_files: Optional[Dict[str, str]] = None
    translated_files: Optional[Dict[str, str]] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def subtitle_file(self) -> Optional[str]:
        """Get main subtitle file path"""
        if not self.original_files:
            return None
        return self.original_files.get("subtitle")
    
    @property
    def metadata_file(self) -> Optional[str]:
        """Get metadata file path"""
        if not self.original_files:
            return None
        return self.original_files.get("metadata")
    
    @property
    def corrected_subtitle_file(self) -> Optional[str]:
        """Get corrected subtitle file path"""
        if not self.corrected_files:
            return None
        return self.corrected_files.get("subtitle")
    
    @property
    def translated_subtitle_file(self) -> Optional[str]:
        """Get translated subtitle file path"""
        if not self.translated_files:
            return None
        return self.translated_files.get("subtitle")
    
    def has_correction(self) -> bool:
        """Check if correction was performed"""
        return self.corrected_files is not None and len(self.corrected_files) > 0
    
    def has_translation(self) -> bool:
        """Check if translation was performed"""
        return self.translated_files is not None and len(self.translated_files) > 0
    
    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"JobResult {status} for {self.job_id[:8]}"