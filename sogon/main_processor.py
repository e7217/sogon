"""
Main processing module - Complete workflow from YouTube link or local file to subtitle generation
"""

import os
import tempfile
from pathlib import Path
import logging
import yt_dlp
from .downloader import download_youtube_audio
from .transcriber import transcribe_audio
from .utils import create_output_directory, save_subtitle_and_metadata
from .audio_manager import AudioFileManager
from .config import get_settings

logger = logging.getLogger(__name__)


def is_url(input_string):
    """
    Check if input string is a URL
    
    Args:
        input_string (str): Input string to check
    
    Returns:
        bool: True if it's a URL, False otherwise
    """
    return input_string.startswith(('http://', 'https://', 'www.')) or 'youtube.com' in input_string or 'youtu.be' in input_string


def file_to_subtitle(
    file_path,
    base_output_dir="./result",
    subtitle_format="txt",
    enable_correction=True,
    use_ai_correction=True,
    keep_audio=False,
):
    """
    Generate subtitles from local audio file
    
    Args:
        file_path (str): Path to local audio file
        base_output_dir (str): Base output directory
        subtitle_format (str): Subtitle format (txt, srt, json)
        enable_correction (bool): Whether to use text correction
        use_ai_correction (bool): Whether to use AI-based correction
        keep_audio (bool): Whether to keep audio files after processing
    
    Returns:
        tuple: (original files, corrected files, output directory)
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None, None, None
        
        # Check if it's a valid audio/video file
        settings = get_settings()
        valid_extensions = ['.' + fmt for fmt in settings.audio_formats + settings.video_formats]
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in valid_extensions:
            logger.error(f"Unsupported file format: {file_ext}. Supported formats: {', '.join(valid_extensions)}")
            return None, None, None
        
        # Get filename without extension for output naming
        file_name = Path(file_path).stem
        logger.info(f"Processing local file: {file_name}")
        
        # Create output directory in date/time/filename format
        output_dir = create_output_directory(base_output_dir, file_name)
        logger.info(f"Output directory created: {output_dir}")
        
        logger.info("Generating subtitles with Groq Whisper Turbo...")
        
        # Speech recognition (including metadata)
        settings = get_settings()
        subtitle_text, metadata = transcribe_audio(file_path, api_key=settings.groq_api_key)
        
        if not subtitle_text:
            logger.error("Speech recognition failed.")
            return None, None, None
        
        # Save subtitle and metadata files (including correction)
        result = save_subtitle_and_metadata(
            subtitle_text,
            metadata,
            output_dir,
            file_name,
            subtitle_format,
            correction_enabled=enable_correction,
            use_ai_correction=use_ai_correction,
            api_key=settings.groq_api_key,
        )
        
        if result and len(result) == 4:
            original_files = result[:3]
            corrected_files = result[3]
            return original_files, corrected_files, output_dir
        else:
            return result[:3] if result else None, None, output_dir
    
    except Exception as e:
        logger.error(f"Error occurred during subtitle generation from file: {e}")
        return None, None, None


def process_input_to_subtitle(
    input_path,
    base_output_dir="./result",
    subtitle_format="txt",
    enable_correction=True,
    use_ai_correction=True,
    keep_audio=False,
):
    """
    Generate subtitles from URL or local file
    
    Args:
        input_path (str): YouTube URL or local file path
        base_output_dir (str): Base output directory
        subtitle_format (str): Subtitle format (txt, srt, json)
        enable_correction (bool): Whether to use text correction
        use_ai_correction (bool): Whether to use AI-based correction
        keep_audio (bool): Whether to keep audio files after processing
    
    Returns:
        tuple: (original files, corrected files, output directory)
    """
    if is_url(input_path):
        logger.info("Input detected as URL, processing with YouTube downloader...")
        return youtube_to_subtitle(
            input_path, base_output_dir, subtitle_format, enable_correction, use_ai_correction, keep_audio
        )
    else:
        logger.info("Input detected as file path, processing local file...")
        return file_to_subtitle(
            input_path, base_output_dir, subtitle_format, enable_correction, use_ai_correction, keep_audio
        )


def youtube_to_subtitle(
    url,
    base_output_dir="./result",
    subtitle_format="txt",
    enable_correction=True,
    use_ai_correction=True,
    keep_audio=False,
):
    """
    Generate subtitles from YouTube link (including correction features)

    Args:
        url (str): YouTube URL
        base_output_dir (str): Base output directory
        subtitle_format (str): Subtitle format (txt, srt, json)
        enable_correction (bool): Whether to use text correction
        use_ai_correction (bool): Whether to use AI-based correction
        keep_audio (bool): Whether to keep audio files after processing

    Returns:
        tuple: (original files, corrected files, output directory)
    """
    try:
        # First get video information to check title
        logger.info("Fetching YouTube video information...")
        ydl_opts = {"quiet": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get("title", "unknown")

        # Create output directory in date/time/title format
        output_dir = create_output_directory(base_output_dir, video_title)
        logger.info(f"Output directory created: {output_dir}")

        logger.info("Downloading audio from YouTube...")
        audio_path = download_youtube_audio(url)

        if not audio_path:
            logger.error("Audio download failed.")
            return None, None, None

        logger.info(f"Audio download completed: {audio_path}")
        logger.info("Generating subtitles with Groq Whisper Turbo...")

        # Speech recognition (including metadata)
        settings = get_settings()
        subtitle_text, metadata = transcribe_audio(audio_path, api_key=settings.groq_api_key)

        if not subtitle_text:
            logger.error("Speech recognition failed.")
            return None, None, None

        # Save subtitle and metadata files (including correction)
        video_name = Path(audio_path).stem
        result = save_subtitle_and_metadata(
            subtitle_text,
            metadata,
            output_dir,
            video_name,
            subtitle_format,
            correction_enabled=enable_correction,
            use_ai_correction=use_ai_correction,
            api_key=settings.groq_api_key,
        )

        # Handle audio file using AudioFileManager
        with AudioFileManager(keep_audio=keep_audio) as audio_manager:
            final_audio_path = audio_manager.handle_downloaded_audio(
                audio_path, output_dir, video_name
            )
            if final_audio_path:
                logger.info(f"Audio file preserved at: {final_audio_path}")

        if result and len(result) == 4:
            original_files = result[:3]
            corrected_files = result[3]
            return original_files, corrected_files, output_dir
        else:
            return result[:3] if result else None, None, output_dir

    except Exception as e:
        logger.error(f"Error occurred during subtitle generation: {e}")
        return None, None, None
