#!/usr/bin/env python3
"""
SOGON - Refactored Main Entry Point
Uses the new Phase 1 & Phase 2 architecture with services and dependency injection
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import Optional
import typer
from typing_extensions import Annotated

# Import new architecture components
from sogon.config import get_settings
from sogon.services.interfaces import (
    AudioService, TranscriptionService, CorrectionService, 
    YouTubeService, FileService, WorkflowService, TranslationService
)
from sogon.services.audio_service import AudioServiceImpl
from sogon.services.transcription_service import TranscriptionServiceImpl
from sogon.services.workflow_service import WorkflowServiceImpl
from sogon.repositories.interfaces import FileRepository
from sogon.repositories.file_repository import FileRepositoryImpl
from sogon.models.job import JobStatus
from sogon.models.translation import SupportedLanguage
from sogon.exceptions.base import SogonError
from sogon.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


class ServiceContainer:
    """Dependency injection container for services"""
    
    def __init__(self):
        self.settings = get_settings()
        self._file_repository: Optional[FileRepository] = None
        self._audio_service: Optional[AudioService] = None
        self._transcription_service: Optional[TranscriptionService] = None
        self._correction_service: Optional[CorrectionService] = None
        self._youtube_service: Optional[YouTubeService] = None
        self._file_service: Optional[FileService] = None
        self._translation_service: Optional[TranslationService] = None
        self._workflow_service: Optional[WorkflowService] = None
    
    @property
    def file_repository(self) -> FileRepository:
        if self._file_repository is None:
            self._file_repository = FileRepositoryImpl()
        return self._file_repository
    
    @property
    def audio_service(self) -> AudioService:
        if self._audio_service is None:
            self._audio_service = AudioServiceImpl(
                max_workers=self.settings.max_workers
            )
        return self._audio_service
    
    @property
    def transcription_service(self) -> TranscriptionService:
        if self._transcription_service is None:
            self._transcription_service = TranscriptionServiceImpl(
                api_key=self.settings.groq_api_key,
                max_workers=self.settings.max_workers
            )
        return self._transcription_service
    
    @property
    def correction_service(self) -> CorrectionService:
        if self._correction_service is None:
            # Import here to avoid circular imports
            from sogon.services.correction_service import CorrectionServiceImpl
            self._correction_service = CorrectionServiceImpl(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                model=self.settings.openai_model,
                temperature=self.settings.openai_temperature
            )
        return self._correction_service
    
    @property
    def youtube_service(self) -> YouTubeService:
        if self._youtube_service is None:
            # Import here to avoid circular imports
            from sogon.services.youtube_service import YouTubeServiceImpl
            self._youtube_service = YouTubeServiceImpl(
                timeout=self.settings.youtube_socket_timeout,
                retries=self.settings.youtube_retries,
                preferred_format=self.settings.youtube_preferred_format
            )
        return self._youtube_service
    
    @property
    def file_service(self) -> FileService:
        if self._file_service is None:
            # Import here to avoid circular imports
            from sogon.services.file_service import FileServiceImpl
            self._file_service = FileServiceImpl(
                file_repository=self.file_repository,
                output_base_dir=Path(self.settings.output_base_dir)
            )
        return self._file_service
    
    @property
    def translation_service(self) -> TranslationService:
        if self._translation_service is None:
            # Import here to avoid circular imports
            from sogon.services.translation_service import TranslationServiceImpl
            self._translation_service = TranslationServiceImpl(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                model=self.settings.openai_model,
                temperature=self.settings.openai_temperature,
                max_concurrent_requests=self.settings.openai_max_concurrent_requests
            )
        return self._translation_service
    
    @property
    def workflow_service(self) -> WorkflowService:
        if self._workflow_service is None:
            self._workflow_service = WorkflowServiceImpl(
                audio_service=self.audio_service,
                transcription_service=self.transcription_service,
                correction_service=self.correction_service,
                youtube_service=self.youtube_service,
                file_service=self.file_service,
                translation_service=self.translation_service
            )
        return self._workflow_service


async def process_input(
    input_path: str,
    services: ServiceContainer,
    output_format: str = "txt",
    enable_correction: bool = True,
    use_ai_correction: bool = True,
    keep_audio: bool = False,
    output_dir: Optional[str] = None,
    enable_translation: bool = False,
    translation_target_language: Optional[str] = None,
    whisper_source_language: Optional[str] = None
) -> bool:
    """
    Process input using the new service architecture
    
    Args:
        input_path: YouTube URL or local file path
        services: Service container with all dependencies
        output_format: Output format (txt, srt, vtt, json)
        enable_correction: Enable text correction
        use_ai_correction: Use AI-based correction
        keep_audio: Keep downloaded audio files
        output_dir: Custom output directory
        enable_translation: Enable translation
        translation_target_language: Target language for translation
        whisper_source_language: Source language for Whisper transcription (auto-detect if None)
        
    Returns:
        bool: True if processing succeeded
    """
    try:
        # Determine output directory
        base_output_dir = Path(output_dir) if output_dir else Path(services.settings.output_base_dir)
        
        # Parse translation target language
        target_lang = None
        if enable_translation and translation_target_language:
            try:
                target_lang = SupportedLanguage(translation_target_language)
            except ValueError:
                logger.error(f"Unsupported translation language: {translation_target_language}")
                return False
        
        # Check if input is URL or local file
        if services.youtube_service.is_valid_url(input_path):
            logger.info(f"Processing YouTube URL: {input_path}")
            job = await services.workflow_service.process_youtube_url(
                url=input_path,
                output_dir=base_output_dir,
                format=output_format,
                enable_correction=enable_correction,
                use_ai_correction=use_ai_correction,
                keep_audio=keep_audio,
                enable_translation=enable_translation,
                translation_target_language=target_lang,
                whisper_source_language=whisper_source_language
            )
        else:
            # Local file processing
            file_path = Path(input_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return False
            
            logger.info(f"Processing local file: {file_path}")
            job = await services.workflow_service.process_local_file(
                file_path=file_path,
                output_dir=base_output_dir,
                format=output_format,
                enable_correction=enable_correction,
                use_ai_correction=use_ai_correction,
                keep_audio=keep_audio,
                enable_translation=enable_translation,
                translation_target_language=target_lang,
                whisper_source_language=whisper_source_language
            )
        
        # Wait for job completion (with timeout)
        max_wait_seconds = services.settings.max_processing_timeout_seconds
        wait_seconds = 0
        
        while wait_seconds < max_wait_seconds:
            status = await services.workflow_service.get_job_status(job.id)
            
            if status == JobStatus.COMPLETED:
                logger.info("Processing completed successfully!")
                logger.info(f"Output directory: {job.actual_output_dir}")
                return True
            elif status == JobStatus.FAILED:
                logger.error(f"Processing failed: {job.error_message}")
                return False
            elif status == JobStatus.NOT_FOUND:
                logger.error("Job not found")
                return False
            
            # Wait and check again
            await asyncio.sleep(2)
            wait_seconds += 2
        
        logger.error("Processing timed out")
        return False
        
    except SogonError as e:
        logger.error(f"SOGON error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


app = typer.Typer(
    name="sogon",
    help="SOGON - AI-powered subtitle generator from YouTube URLs or local audio files",
    rich_markup_mode="rich",
    add_completion=False,
    epilog="""Examples:
  sogon "https://youtube.com/watch?v=..." 
  sogon "audio.mp3" --format srt
  sogon "video.mp4" --no-correction --output-dir ./results
  sogon "video.mp4" --translate --target-language ko
"""
)


@app.command("run")
def process(
    input_path: Annotated[str, typer.Argument(help="YouTube URL or local audio/video file path")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output subtitle format")] = "txt",
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", "-o", help="Output directory (default: ./result)")] = None,
    no_correction: Annotated[bool, typer.Option("--no-correction", help="Disable text correction")] = False,
    no_ai_correction: Annotated[bool, typer.Option("--no-ai-correction", help="Disable AI-based text correction")] = False,
    keep_audio: Annotated[bool, typer.Option("--keep-audio", help="Keep downloaded audio files")] = False,
    translate: Annotated[bool, typer.Option("--translate", help="Enable translation of subtitles")] = False,
    target_language: Annotated[Optional[str], typer.Option("--target-language", "-t", help="Target language for translation (e.g., ko, en, ja, zh-cn)")] = None,
    source_language: Annotated[Optional[str], typer.Option("--source-language", "-s", help="Source language for Whisper transcription (auto-detect if not specified)")] = None,
    log_level: Annotated[str, typer.Option("--log-level", help="Logging level")] = "INFO"
):
    """Process video/audio file for subtitle generation"""
    
    # Validate format
    if format not in ["txt", "srt", "vtt", "json"]:
        typer.echo(f"Error: Invalid format '{format}'. Choose from: txt, srt, vtt, json", err=True)
        raise typer.Exit(1)
    
    # Validate log level
    if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
        typer.echo(f"Error: Invalid log level '{log_level}'. Choose from: DEBUG, INFO, WARNING, ERROR", err=True)
        raise typer.Exit(1)
    
    # Setup logging
    setup_logging(console_level=log_level, file_level=log_level)
    
    typer.echo("SOGON - Subtitle Generator (Refactored Architecture)")
    typer.echo("=" * 60)
    
    # Validate translation options
    if translate:
        if not target_language:
            typer.echo("Error: --target-language is required when --translate is enabled", err=True)
            typer.echo("Use 'sogon list-languages' to see supported languages")
            raise typer.Exit(1)
        
        # Validate target language
        try:
            SupportedLanguage(target_language)
        except ValueError:
            typer.echo(f"Error: Unsupported target language: {target_language}", err=True)
            typer.echo("Use 'sogon list-languages' to see supported languages")
            raise typer.Exit(1)
    
    # Initialize service container
    services = ServiceContainer()
    
    # Log configuration
    logger.info(f"Input: {input_path}")
    logger.info(f"Format: {format.upper()}")
    logger.info(f"Text correction: {'disabled' if no_correction else 'enabled'}")
    logger.info(f"AI correction: {'disabled' if no_ai_correction else 'enabled'}")
    logger.info(f"Keep audio: {'yes' if keep_audio else 'no'}")
    if translate:
        logger.info(f"Translation: → {target_language}")
    else:
        logger.info("Translation: disabled")
    logger.info(f"Whisper source language: {source_language or 'auto'}")
    logger.info("-" * 60)
    
    try:
        # Process input
        success = asyncio.run(
            process_input(
                input_path=input_path,
                services=services,
                output_format=format,
                enable_correction=not no_correction,
                use_ai_correction=not no_ai_correction,
                keep_audio=keep_audio,
                output_dir=output_dir,
                enable_translation=translate,
                translation_target_language=target_language,
                whisper_source_language=source_language
            )
        )
        
        if success:
            typer.echo("Processing completed successfully!", color=typer.colors.GREEN)
        else:
            typer.echo("Processing failed!", err=True, color=typer.colors.RED)
            raise typer.Exit(1)
            
    except KeyboardInterrupt:
        typer.echo("\nInterrupted by user", color=typer.colors.YELLOW)
        raise typer.Exit(130)
    except Exception as e:
        typer.echo(f"Fatal error: {e}", err=True, color=typer.colors.RED)
        raise typer.Exit(1)


@app.command("list-languages")
def list_languages():
    """List supported translation languages"""
    typer.echo("Supported Translation Languages:")
    typer.echo("=" * 40)
    for lang in SupportedLanguage:
        typer.echo(f"  {lang.value:<6} - {lang.display_name}")


def main():
    """Main entry point for CLI"""
    app()


if __name__ == "__main__":
    main()