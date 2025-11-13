"""
Workflow service implementation - Orchestrates complete processing workflows
"""

import asyncio
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from .interfaces import WorkflowService, AudioService, TranscriptionService, YouTubeService, FileService, TranslationService
from ..models.job import ProcessingJob, JobStatus, JobType
from ..models.audio import AudioFile
from ..models.translation import SupportedLanguage, TranslationResult
from ..models.transcription import TranscriptionResult, TranscriptionSegment
from ..exceptions.job import JobError
from ..config import get_settings

logger = logging.getLogger(__name__)


class WorkflowServiceImpl(WorkflowService):
    """Implementation of WorkflowService interface"""
    
    def __init__(
        self,
        audio_service: AudioService,
        transcription_service: TranscriptionService,
        youtube_service: YouTubeService,
        file_service: FileService,
        translation_service: Optional[TranslationService] = None
    ):
        self.audio_service = audio_service
        self.transcription_service = transcription_service
        self.youtube_service = youtube_service
        self.file_service = file_service
        self.translation_service = translation_service
        self.settings = get_settings()

        # In-memory job storage (in production, use repository)
        self._jobs = {}
    
    async def process_youtube_url(
        self,
        url: str,
        output_dir: Path,
        format: str = "txt",
        keep_audio: bool = False,
        enable_translation: bool = False,
        translation_target_language: Optional[SupportedLanguage] = None,
        whisper_source_language: Optional[str] = None,
        whisper_model: Optional[str] = None,
        whisper_base_url: Optional[str] = None,
        job: Optional[ProcessingJob] = None
    ) -> ProcessingJob:
        """Complete workflow for YouTube URL processing"""

        # Import here to avoid circular imports
        from ..config import get_settings
        settings = get_settings()

        # Use provided job or create new one (for CLI compatibility)
        if job is None:
            job_id = str(uuid.uuid4())
            job = ProcessingJob(
                id=job_id,
                job_type=JobType.YOUTUBE_URL,
                input_path=url,
                output_directory=str(output_dir),
                subtitle_format=format,
                keep_audio=keep_audio,
                enable_translation=enable_translation,
                translation_target_language=translation_target_language.value if translation_target_language else None,
                whisper_source_language=whisper_source_language,
                whisper_model=whisper_model,
                whisper_base_url=whisper_base_url,
                status=JobStatus.PENDING,
                created_at=datetime.now()
            )

            self._jobs[job.id] = job

            # Start processing in background (CLI mode)
            asyncio.create_task(self._process_youtube_workflow(job))
        else:
            # Worker mode - process synchronously
            await self._process_youtube_workflow(job)

        return job
    
    async def process_local_file(
        self,
        file_path: Path,
        output_dir: Path,
        format: str = "txt",
        keep_audio: bool = False,
        enable_translation: bool = False,
        translation_target_language: Optional[SupportedLanguage] = None,
        whisper_source_language: Optional[str] = None,
        whisper_model: Optional[str] = None,
        whisper_base_url: Optional[str] = None,
        job: Optional[ProcessingJob] = None
    ) -> ProcessingJob:
        """Complete workflow for local file processing"""

        # Import here to avoid circular imports
        from ..config import get_settings
        settings = get_settings()

        # Use provided job or create new one (for CLI compatibility)
        if job is None:
            job_id = str(uuid.uuid4())
            job = ProcessingJob(
                id=job_id,
                job_type=JobType.LOCAL_FILE,
                input_path=str(file_path),
                output_directory=str(output_dir),
                subtitle_format=format,
                keep_audio=keep_audio,
                enable_translation=enable_translation,
                translation_target_language=translation_target_language.value if translation_target_language else None,
                whisper_source_language=whisper_source_language,
                whisper_model=whisper_model,
                whisper_base_url=whisper_base_url,
                status=JobStatus.PENDING,
                created_at=datetime.now()
            )

            self._jobs[job.id] = job

            # Start processing in background (CLI mode)
            asyncio.create_task(self._process_local_file_workflow(job))
        else:
            # Worker mode - process synchronously
            await self._process_local_file_workflow(job)

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
            job.actual_output_dir = str(actual_output_dir)
            
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
            
            # Step 2: Check if file is video and extract audio if needed
            file_extension = file_path.suffix.lstrip('.').lower()
            
            if file_extension in self.settings.video_formats:
                # Video file - extract audio first
                logger.info(f"Detected video file, extracting audio from {file_path}")
                # Create a temporary directory for audio extraction
                import tempfile
                temp_dir = Path(tempfile.mkdtemp())
                audio_path = await self.audio_service.extract_audio_from_video(
                    file_path, temp_dir
                )
                audio_file = await self.audio_service.get_audio_info(audio_path)
                # Mark for cleanup after processing
                cleanup_extracted_audio = True
            else:
                # Regular audio file
                audio_file = await self.audio_service.get_audio_info(file_path)
                cleanup_extracted_audio = False
            
            # Step 3: Validate audio format (check both audio and video formats)
            all_supported_formats = self.settings.audio_formats + self.settings.video_formats
            is_valid = await self.audio_service.validate_format(
                audio_file, all_supported_formats
            )
            if not is_valid and file_extension not in self.settings.video_formats:
                raise JobError(f"Unsupported file format: {file_extension}")
            
            # Step 4: Create output directory
            actual_output_dir = await self.file_service.create_output_directory(
                Path(job.output_directory), audio_file.stem
            )
            job.actual_output_dir = str(actual_output_dir)
            
            # Step 5: Process audio file
            await self._process_audio_file(job, audio_file, audio_file.stem)
            
            # Step 6: Handle extracted audio based on keep_audio setting
            if cleanup_extracted_audio and audio_file.path.exists():
                if job.keep_audio:
                    # Copy extracted audio to output directory
                    import shutil
                    output_audio_path = actual_output_dir / audio_file.path.name
                    try:
                        shutil.copy2(audio_file.path, output_audio_path)
                        logger.info(f"Saved extracted audio to: {output_audio_path}")
                    except Exception as e:
                        logger.warning(f"Failed to save extracted audio: {e}")
                
                # Always cleanup temp file
                try:
                    audio_file.path.unlink()
                    logger.debug(f"Cleaned up temporary audio: {audio_file.path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary audio: {e}")
            
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
                transcription = await self.transcription_service.transcribe_audio(audio_file, job.whisper_source_language, job.whisper_model, job.whisper_base_url)
            else:
                # Multiple chunks transcription
                chunk_results = await self.transcription_service.transcribe_chunks(chunks, job.whisper_source_language, job.whisper_model, job.whisper_base_url)
                transcription = await self.transcription_service.combine_transcriptions(chunk_results)
            
            if not transcription.text.strip():
                raise JobError("Transcription returned empty result")
            
            # Step 3: Save original transcription
            output_dir = Path(job.actual_output_dir)
            await self.file_service.save_transcription(
                transcription, output_dir, base_name, job.subtitle_format
            )
            await self.file_service.save_timestamps(
                transcription, output_dir, base_name
            )
            await self.file_service.save_metadata(
                transcription.to_dict(), output_dir, base_name
            )
            
            # Step 4: Apply translation if enabled
            if job.enable_translation and job.translation_target_language and self.translation_service:
                logger.info(f"Applying translation to {job.translation_target_language}")
                job.status = JobStatus.TRANSLATING
                
                target_language = SupportedLanguage(job.translation_target_language)
                translation_result = await self.translation_service.translate_transcription(
                    transcription, target_language, job.whisper_source_language
                )
                
                # Save translated version
                suffix = "_translated"
                
                # Convert translation result to transcription format for saving
                translated_transcription = self._translation_to_transcription(translation_result, transcription)

                await self.file_service.save_transcription(
                    translated_transcription, output_dir, f"{base_name}{suffix}", job.subtitle_format
                )
                await self.file_service.save_timestamps(
                    translated_transcription, output_dir, f"{base_name}{suffix}"
                )
                await self.file_service.save_metadata(
                    translation_result.to_dict(), output_dir, f"{base_name}{suffix}"
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
    
    def _translation_to_transcription(
        self, 
        translation_result: TranslationResult, 
        original_transcription: TranscriptionResult
    ) -> TranscriptionResult:
        """Convert translation result to transcription format for saving compatibility"""
        # Convert translation segments to transcription segments
        transcription_segments = []
        if translation_result.segments:
            for i, trans_seg in enumerate(translation_result.segments, 1):
                transcription_segments.append(TranscriptionSegment(
                    id=i,
                    start=trans_seg.start_time,
                    end=trans_seg.end_time,
                    text=trans_seg.translated_text,
                    confidence=trans_seg.confidence_score
                ))
        
        return TranscriptionResult(
            text=translation_result.translated_text,
            language=translation_result.target_language.value,
            duration=original_transcription.duration,
            segments=transcription_segments,
            model_used=f"translation_{translation_result.model_used}",
            confidence=original_transcription.confidence
        )