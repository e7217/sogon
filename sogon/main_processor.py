"""
Main processing module - Complete workflow from YouTube link to subtitle generation
"""

import os
import tempfile
from pathlib import Path
import logging
import yt_dlp
from .downloader import download_youtube_audio
from .transcriber import transcribe_audio
from .utils import create_output_directory, save_subtitle_and_metadata

logger = logging.getLogger(__name__)


def youtube_to_subtitle(
    url,
    base_output_dir="./result",
    subtitle_format="txt",
    enable_correction=True,
    use_ai_correction=True,
):
    """
    Generate subtitles from YouTube link (including correction features)

    Args:
        url (str): YouTube URL
        base_output_dir (str): Base output directory
        subtitle_format (str): Subtitle format (txt, srt)
        enable_correction (bool): Whether to use text correction
        use_ai_correction (bool): Whether to use AI-based correction

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
        subtitle_text, metadata = transcribe_audio(audio_path)

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
        )

        # Delete temporary audio file
        try:
            os.remove(audio_path)
            temp_dir = os.path.dirname(audio_path)
            if temp_dir.startswith(tempfile.gettempdir()):
                os.rmdir(temp_dir)
        except OSError:
            pass

        if result and len(result) == 4:
            original_files = result[:3]
            corrected_files = result[3]
            return original_files, corrected_files, output_dir
        else:
            return result[:3] if result else None, None, output_dir

    except Exception as e:
        logger.error(f"Error occurred during subtitle generation: {e}")
        return None, None, None
