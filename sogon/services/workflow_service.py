"""
Workflow service implementation - Orchestrates complete processing workflows
"""

import asyncio
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from .interfaces import WorkflowService, AudioService, TranscriptionService, CorrectionService, YouTubeService, FileService
from ..models.job import ProcessingJob, JobStatus, JobType
from ..models.audio import AudioFile
from ..exceptions.job import JobError
from ..config import get_settings

logger = logging.getLogger(__name__)


class WorkflowServiceImpl(WorkflowService):
    """Implementation of WorkflowService interface"""
    
    def __init__(
        self,
        audio_service: AudioService,
        transcription_service: TranscriptionService,
        correction_service: CorrectionService,
        youtube_service: YouTubeService,
        file_service: FileService
    ):
        self.audio_service = audio_service
        self.transcription_service = transcription_service
        self.correction_service = correction_service
        self.youtube_service = youtube_service
        self.file_service = file_service
        self.settings = get_settings()
        
        # In-memory job storage (in production, use repository)
        self._jobs = {}
    
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
        
        job_id = str(uuid.uuid4())
        job = ProcessingJob(
            id=job_id,
            job_type=JobType.YOUTUBE_URL,
            input_path=url,
            output_directory=str(output_dir),
            subtitle_format=format,
            enable_correction=enable_correction,
            use_ai_correction=use_ai_correction,
            keep_audio=keep_audio,
            status=JobStatus.PENDING,
            created_at=datetime.now()
        )
        
        self._jobs[job_id] = job
        
        # Start processing in background
        asyncio.create_task(self._process_youtube_workflow(job))
        
        return job
    
    async def process_local_file(
        self,
        file_path: Path,
        output_dir: Path,
        format: str = "txt",
        enable_correction: bool = True,
        use_ai_correction: bool = True
    ) -> ProcessingJob:
        """Complete workflow for local file processing"""
        
        job_id = str(uuid.uuid4())
        job = ProcessingJob(
            id=job_id,
            job_type=JobType.LOCAL_FILE,
            input_path=str(file_path),
            output_directory=str(output_dir),
            subtitle_format=format,
            enable_correction=enable_correction,
            use_ai_correction=use_ai_correction,
            keep_audio=False,  # Local files are not downloaded
            status=JobStatus.PENDING,
            created_at=datetime.now()
        )
        
        self._jobs[job_id] = job
        
        # Start processing in background
        asyncio.create_task(self._process_local_file_workflow(job))
        
        return job
    
    async def get_job_status(self, job_id: str) -> JobStatus:
        """Get processing job status"""
        job = self._jobs.get(job_id)
        return job.status if job else JobStatus.NOT_FOUND
    
    async def _process_youtube_workflow(self, job: ProcessingJob) -> None:
        """Internal workflow for YouTube URL processing"""
        try:
            # Update job status
            job.status = JobStatus.DOWNLOADING
            job.started_at = datetime.now()
            
            logger.info(f"Starting YouTube workflow for job {job.id}")
            
            # Step 1: Validate YouTube URL
            if not self.youtube_service.is_valid_url(job.input_path):
                raise JobError(f"Invalid YouTube URL: {job.input_path}")
            
            # Step 2: Get video info and create output directory
            video_info = await self.youtube_service.get_video_info(job.input_path)
            video_title = video_info.get("title", "unknown_video")
            
            actual_output_dir = await self.file_service.create_output_directory(
                Path(job.output_directory), video_title
            )
            job.actual_output_dir = actual_output_dir
            
            # Step 3: Download audio
            logger.info(f"Downloading audio from {job.input_path}")
            audio_file = await self.youtube_service.download_audio(job.input_path, actual_output_dir)
            
            # Step 4: Process audio file
            await self._process_audio_file(job, audio_file, video_title)
            
            # Step 5: Cleanup if not keeping audio
            if not job.keep_audio and audio_file.exists:
                try:
                    audio_file.path.unlink()
                    logger.info(f"Cleaned up downloaded audio: {audio_file.path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup audio file: {e}")
            
            # Mark job as completed
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            logger.info(f"YouTube workflow completed for job {job.id}")
            
        except Exception as e:
            logger.error(f"YouTube workflow failed for job {job.id}: {e}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
    
    async def _process_local_file_workflow(self, job: ProcessingJob) -> None:
        """Internal workflow for local file processing"""
        try:
            # Update job status
            job.status = JobStatus.DOWNLOADING
            job.started_at = datetime.now()
            
            logger.info(f"Starting local file workflow for job {job.id}")
            
            # Step 1: Validate file exists
            file_path = Path(job.input_path)
            if not file_path.exists():
                raise JobError(f"File not found: {file_path}")
            
            # Step 2: Get audio file info
            audio_file = await self.audio_service.get_audio_info(file_path)
            
            # Step 3: Validate audio format
            is_valid = await self.audio_service.validate_format(
                audio_file, self.settings.audio_formats
            )
            if not is_valid:
                raise JobError(f"Unsupported audio format: {audio_file.format}")
            
            # Step 4: Create output directory
            actual_output_dir = await self.file_service.create_output_directory(
                Path(job.output_directory), audio_file.stem
            )
            job.actual_output_dir = actual_output_dir
            
            # Step 5: Process audio file
            await self._process_audio_file(job, audio_file, audio_file.stem)
            
            # Mark job as completed
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            logger.info(f"Local file workflow completed for job {job.id}")
            
        except Exception as e:
            logger.error(f"Local file workflow failed for job {job.id}: {e}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
    
    async def _process_audio_file(self, job: ProcessingJob, audio_file: AudioFile, base_name: str) -> None:
        """Common audio processing logic"""
        try:
            # Step 1: Split audio if needed
            logger.info(f"Analyzing audio file: {audio_file}")
            chunks = await self.audio_service.split_audio(
                audio_file, self.settings.max_chunk_size_mb
            )
            
            # Step 2: Transcribe audio
            logger.info(f"Transcribing {len(chunks)} audio chunks")
            if len(chunks) == 1:
                # Single file transcription
                transcription = await self.transcription_service.transcribe_audio(audio_file)
            else:
                # Multiple chunks transcription
                chunk_results = await self.transcription_service.transcribe_chunks(chunks)
                transcription = await self.transcription_service.combine_transcriptions(chunk_results)
            
            if not transcription.text.strip():
                raise JobError("Transcription returned empty result")
            
            # Step 3: Save original transcription
            await self.file_service.save_transcription(
                transcription, job.actual_output_dir, base_name, job.subtitle_format
            )
            await self.file_service.save_timestamps(
                transcription, job.actual_output_dir, base_name
            )
            await self.file_service.save_metadata(
                transcription.to_dict(), job.actual_output_dir, base_name
            )
            
            # Step 4: Apply correction if enabled
            if job.enable_correction:
                logger.info("Applying text correction")
                corrected_transcription = await self.correction_service.correct_transcription(
                    transcription, job.use_ai_correction
                )
                
                # Save corrected version
                await self.file_service.save_transcription(
                    corrected_transcription, job.actual_output_dir, f"{base_name}_corrected", job.subtitle_format
                )
                await self.file_service.save_timestamps(
                    corrected_transcription, job.actual_output_dir, f"{base_name}_corrected"
                )
                await self.file_service.save_metadata(
                    corrected_transcription.to_dict(), job.actual_output_dir, f"{base_name}_corrected"
                )
            
            # Step 5: Cleanup chunks if multiple were created
            if len(chunks) > 1:
                await self.audio_service.cleanup_chunks(chunks)
            
            logger.info(f"Audio processing completed for {audio_file.name}")
            
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            # Cleanup chunks on error
            if 'chunks' in locals() and len(chunks) > 1:
                try:
                    await self.audio_service.cleanup_chunks(chunks)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup chunks after error: {cleanup_error}")
            raise