"""
YouTube audio download module
"""

import os
import tempfile
import re
import logging
import yt_dlp
from pydub import AudioSegment

logger = logging.getLogger(__name__)


def download_youtube_audio(url, output_dir=None):
    """
    Download audio from YouTube video

    Args:
        url (str): YouTube URL
        output_dir (str): Output directory (uses temporary directory if not provided)

    Returns:
        str: Downloaded audio file path
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp()

    # Configure yt-dlp options (download speed optimization)
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",  # Prefer m4a for speed improvement
        "extractaudio": True,
        "audioformat": "wav",
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "socket_timeout": 30,  # Reduced socket timeout (default 60s → 30s)
        "retries": 3,  # Reduced retry count (default 10 → 3)
        "fragment_retries": 3,  # Reduced fragment retry count
        "http_chunk_size": 5242880,  # Set HTTP chunk size to 5MB
        "concurrent_fragment_downloads": 4,  # 4 concurrent fragment downloads
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "128",  # Lower quality for speed improvement (192 → 128)
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video information
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "unknown")

            # Remove special characters from filename
            safe_title = re.sub(r'[<>:"/\\|?*]', "", title)
            output_path = os.path.join(output_dir, f"{safe_title}.wav")

            # Download
            ydl.download([url])

            # Find downloaded file
            for file in os.listdir(output_dir):
                if file.endswith(".wav"):
                    return os.path.join(output_dir, file)

            return output_path

    except Exception as e:
        logger.error(f"Error occurred during YouTube audio download: {e}, cause: {e.__cause__ or 'unknown'}")
        logger.debug(f"YouTube download detailed error: {type(e).__name__}: {str(e)}")
        if e.__cause__:
            logger.debug(f"YouTube download root cause: {type(e.__cause__).__name__}: {str(e.__cause__)}")
        return None


def split_audio_by_size(audio_path, max_size_mb=24):
    """
    Split audio file based on size

    Args:
        audio_path (str): Audio file path
        max_size_mb (int): Maximum file size (MB)

    Returns:
        list: List of split audio file paths
    """
    try:
        # Check file size
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

        if file_size_mb <= max_size_mb:
            return [audio_path]

        # Load audio with pydub
        audio = AudioSegment.from_wav(audio_path)

        # Calculate chunk length (based on file size)
        total_duration = len(audio)  # milliseconds
        chunk_duration = int(
            (max_size_mb / file_size_mb) * total_duration * 0.9
        )  # safety margin

        chunks = []
        temp_dir = os.path.dirname(audio_path)
        base_name = os.path.splitext(os.path.basename(audio_path))[0]

        # Split audio
        for i, start_time in enumerate(range(0, total_duration, chunk_duration)):
            end_time = min(start_time + chunk_duration, total_duration)
            chunk = audio[start_time:end_time]

            chunk_path = os.path.join(temp_dir, f"{base_name}_chunk_{i + 1}.wav")
            chunk.export(chunk_path, format="wav")
            chunks.append(chunk_path)

        return chunks

    except Exception as e:
        logger.error(f"Error occurred during audio splitting: {e}, cause: {e.__cause__ or 'unknown'}")
        logger.debug(f"Audio splitting detailed error: {type(e).__name__}: {str(e)}")
        if e.__cause__:
            logger.debug(f"Audio splitting root cause: {type(e.__cause__).__name__}: {str(e.__cause__)}")
        return [audio_path]
