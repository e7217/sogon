#!/usr/bin/env python3
"""
SOGON - Refactored Main Entry Point
Uses the new Phase 1 & Phase 2 architecture with services and dependency injection
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

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


def setup_argument_parser() -> argparse.ArgumentParser:
    """Setup command line argument parser"""
    parser = argparse.ArgumentParser(
        description="SOGON - YouTube/Audio to Subtitle Generator (Refactored)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "https://youtube.com/watch?v=..." 
  python main.py "audio.mp3" --format srt
  python main.py "video.mp4" --no-correction --output-dir ./results
  python main.py "video.mp4" --translate --target-language ko
  python main.py "video.mp4" --source-language en --translate -t ko
  python main.py "korean_video.mp4" -s ko --format srt
  python main.py "english_audio.mp3" --source-language en
  python main.py --list-languages
        """
    )
    
    parser.add_argument(
        "input",
        help="YouTube URL or local audio/video file path"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["txt", "srt", "vtt", "json"],
        default="txt",
        help="Output subtitle format (default: txt)"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory (default: ./result)"
    )
    
    parser.add_argument(
        "--no-correction",
        action="store_true",
        help="Disable text correction"
    )
    
    parser.add_argument(
        "--no-ai-correction",
        action="store_true", 
        help="Disable AI-based text correction"
    )
    
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep downloaded audio files"
    )
    
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Enable translation of subtitles"
    )
    
    parser.add_argument(
        "--target-language", "-t",
        help="Target language for translation (e.g., ko, en, ja, zh-cn)"
    )
    
    parser.add_argument(
        "--source-language", "-s",
        help="Source language for Whisper transcription (auto-detect if not specified)"
    )
    
    parser.add_argument(
        "--list-languages",
        action="store_true",
        help="List supported translation languages and exit"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    return parser


async def main():
    """Main entry point"""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Handle --list-languages
    if args.list_languages:
        print("Supported Translation Languages:")
        print("=" * 40)
        for lang in SupportedLanguage:
            print(f"  {lang.value:<6} - {lang.display_name}")
        sys.exit(0)
    
    # Setup logging
    setup_logging(console_level=args.log_level, file_level=args.log_level)
    
    logger.info("SOGON - Subtitle Generator (Refactored Architecture)")
    logger.info("=" * 60)
    
    try:
        # Validate translation options
        if args.translate:
            if not args.target_language:
                logger.error("--target-language is required when --translate is enabled")
                logger.info("Use --list-languages to see supported languages")
                sys.exit(1)
            
            # Validate target language
            try:
                SupportedLanguage(args.target_language)
            except ValueError:
                logger.error(f"Unsupported target language: {args.target_language}")
                logger.info("Use --list-languages to see supported languages")
                sys.exit(1)
        
        # Initialize service container
        services = ServiceContainer()
        
        # Log configuration
        logger.info(f"Input: {args.input}")
        logger.info(f"Format: {args.format.upper()}")
        logger.info(f"Text correction: {'disabled' if args.no_correction else 'enabled'}")
        logger.info(f"AI correction: {'disabled' if args.no_ai_correction else 'enabled'}")
        logger.info(f"Keep audio: {'yes' if args.keep_audio else 'no'}")
        if args.translate:
            logger.info(f"Translation: → {args.target_language}")
        else:
            logger.info("Translation: disabled")
        logger.info(f"Whisper source language: {args.source_language or 'auto'}")
        logger.info("-" * 60)
        
        # Process input
        success = await process_input(
            input_path=args.input,
            services=services,
            output_format=args.format,
            enable_correction=not args.no_correction,
            use_ai_correction=not args.no_ai_correction,
            keep_audio=args.keep_audio,
            output_dir=args.output_dir,
            enable_translation=args.translate,
            translation_target_language=args.target_language,
            whisper_source_language=args.source_language
        )
        
        if success:
            logger.info("Processing completed successfully!")
            sys.exit(0)
        else:
            logger.error("Processing failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())