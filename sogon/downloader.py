"""
YouTube audio download module
"""

import os
import tempfile
import re
import logging
import yt_dlp
from pydub import AudioSegment
from tqdm import tqdm

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
        "audioformat": "mp3",
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "socket_timeout": 30,  # Reduced socket timeout (default 60s → 30s)
        "retries": 3,  # Reduced retry count (default 10 → 3)
        "fragment_retries": 3,  # Reduced fragment retry count
        "http_chunk_size": 5242880,  # Set HTTP chunk size to 5MB
        "concurrent_fragment_downloads": 4,  # 4 concurrent fragment downloads
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
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
            output_path = os.path.join(output_dir, f"{safe_title}.mp3")

            # Download
            ydl.download([url])

            # Find downloaded file
            for file in os.listdir(output_dir):
                if file.endswith(".mp3"):
                    return os.path.join(output_dir, file)

            return output_path

    except Exception as e:
        logger.error(f"Error occurred during YouTube audio download: {e}, cause: {e.__cause__ or 'unknown'}")
        logger.debug(f"YouTube download detailed error: {type(e).__name__}: {str(e)}")
        if e.__cause__:
            logger.debug(f"YouTube download root cause: {type(e.__cause__).__name__}: {str(e.__cause__)}")
        return None


def split_audio_by_size(audio_path, max_chunk_size_mb=24):
    """
    Split audio file into size-based chunks to ensure API compatibility
    
    Note: Uses intelligent duration estimation based on original file bitrate
    to minimize unnecessary chunk creation while staying under 25MB API limit.

    Args:
        audio_path (str): Audio file path
        max_chunk_size_mb (int): Maximum chunk size in MB (default 24MB)

    Returns:
        list: List of split audio file paths
    """
    try:
        # Load audio with pydub (auto-detect format)
        audio = AudioSegment.from_file(audio_path)

        # Convert MB to bytes
        max_chunk_size_bytes = max_chunk_size_mb * 1024 * 1024
        
        # Check original file size
        original_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        if original_size_mb <= max_chunk_size_mb:
            logger.info(f"Audio file size ({original_size_mb:.1f} MB) is within limit ({max_chunk_size_mb} MB), no splitting needed")
            return [audio_path]
            
        # Calculate optimal chunk duration based on original file properties
        total_duration_ms = len(audio)
        original_bitrate_kbps = (original_size_mb * 1024 * 8) / (total_duration_ms / 1000)  # kbps
        
        # Estimate target duration for max chunk size (with safety margin)
        target_chunk_size_mb = max_chunk_size_mb * 0.9  # 90% of limit for safety
        estimated_chunk_duration_ms = int((target_chunk_size_mb * 1024 * 8 * 1000) / original_bitrate_kbps)
        
        logger.info(f"Original file: {original_size_mb:.1f}MB, {total_duration_ms/1000/60:.1f}min, ~{original_bitrate_kbps:.0f}kbps")
        logger.info(f"Estimated chunk duration: {estimated_chunk_duration_ms/1000/60:.1f} minutes")

        chunks = []
        temp_dir = os.path.dirname(audio_path)
        base_name = os.path.splitext(os.path.basename(audio_path))[0]

        # Split audio into size-based chunks
        chunk_index = 0
        start_time = 0
        
        # Calculate approximate number of chunks for progress bar
        estimated_chunks = max(1, int(total_duration_ms / estimated_chunk_duration_ms) + 1)
        
        with tqdm(total=estimated_chunks, desc="Splitting audio", unit="chunk") as pbar:
            while start_time < total_duration_ms:
                chunk_index += 1
                
                # Calculate optimal chunk duration for target size
                remaining_duration = total_duration_ms - start_time
                min_duration = 30000  # 30 seconds minimum
                
                # If remaining time is less than minimum, process it all
                if remaining_duration <= min_duration:
                    best_duration = remaining_duration
                else:
                    # Use estimated duration as starting point, then fine-tune
                    target_duration = min(estimated_chunk_duration_ms, remaining_duration)
                    
                    # Test the estimated duration first
                    end_time = min(start_time + target_duration, total_duration_ms)
                    test_chunk = audio[start_time:end_time]
                    
                    temp_path = os.path.join(temp_dir, f"temp_test_chunk_{chunk_index}.mp3")
                    test_chunk.export(temp_path, format="mp3", bitrate="128k")
                    
                    chunk_size_bytes = os.path.getsize(temp_path)
                    os.remove(temp_path)
                    
                    if chunk_size_bytes <= max_chunk_size_bytes:
                        # Estimated duration works, try to make it larger
                        best_duration = target_duration
                        
                        # Try to extend by 1-2 minutes if possible
                        for extra_minutes in [1, 2]:
                            extended_duration = target_duration + (extra_minutes * 60 * 1000)
                            if start_time + extended_duration <= total_duration_ms:
                                end_time = start_time + extended_duration
                                test_chunk = audio[start_time:end_time]
                                
                                temp_path = os.path.join(temp_dir, f"temp_test_chunk_{chunk_index}_ext.mp3")
                                test_chunk.export(temp_path, format="mp3", bitrate="128k")
                                
                                chunk_size_bytes = os.path.getsize(temp_path)
                                os.remove(temp_path)
                                
                                if chunk_size_bytes <= max_chunk_size_bytes:
                                    best_duration = extended_duration
                                else:
                                    break
                    else:
                        # Estimated duration too large, reduce it
                        best_duration = max(min_duration, target_duration // 2)
                
                # Create the actual chunk with best duration
                end_time = min(start_time + best_duration, total_duration_ms)
                chunk = audio[start_time:end_time]
                
                # Skip chunks that are too short (less than 30 seconds)
                chunk_duration_seconds = (end_time - start_time) / 1000
                if chunk_duration_seconds < 30.0:
                    logger.debug(f"Skipping chunk {chunk_index}: too short ({chunk_duration_seconds:.1f} seconds)")
                    break
                
                chunk_path = os.path.join(temp_dir, f"{base_name}_chunk_{chunk_index}.mp3")
                chunk.export(chunk_path, format="mp3", bitrate="128k")
                
                # Check exported chunk size
                chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)
                chunks.append(chunk_path)
                logger.debug(f"Created chunk {chunk_index}: {chunk_path} ({chunk_duration_seconds/60:.1f} min, {chunk_size_mb:.1f} MB)")
                
                # Update progress bar
                pbar.update(1)
                pbar.set_postfix(size=f"{chunk_size_mb:.1f}MB", duration=f"{chunk_duration_seconds/60:.1f}min")
                
                start_time = end_time

        logger.info(f"Split audio into {len(chunks)} chunks (estimated: {estimated_chunks}) of max {max_chunk_size_mb} MB each")
        return chunks

    except Exception as e:
        logger.error(f"Error occurred during audio splitting: {e}, cause: {e.__cause__ or 'unknown'}")
        logger.debug(f"Audio splitting detailed error: {type(e).__name__}: {str(e)}")
        if e.__cause__:
            logger.debug(f"Audio splitting root cause: {type(e.__cause__).__name__}: {str(e.__cause__)}")
        # Return empty list to indicate failure, not the original file
        return []
