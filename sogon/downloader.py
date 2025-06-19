"""
YouTube audio download module
"""

import os
import tempfile
import re
import logging
from pathlib import Path
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
        "audioformat": "m4a",  # Keep original m4a format to avoid unnecessary conversion
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "socket_timeout": 30,  # Reduced socket timeout (default 60s → 30s)
        "retries": 3,  # Reduced retry count (default 10 → 3)
        "fragment_retries": 3,  # Reduced fragment retry count
        "http_chunk_size": 5242880,  # Set HTTP chunk size to 5MB
        "concurrent_fragment_downloads": 4,  # 4 concurrent fragment downloads
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",  # Keep m4a format
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

            # Find downloaded file (m4a or mp3)
            for file in os.listdir(output_dir):
                if file.endswith((".m4a", ".mp3")):
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
    
    Uses ffmpeg directly to avoid memory issues with large files.
    Temporarily renames files with special characters to avoid subprocess issues.

    Args:
        audio_path (str): Audio file path
        max_chunk_size_mb (int): Maximum chunk size in MB (default 24MB)

    Returns:
        list: List of split audio file paths
    """
    import subprocess
    import json
    import hashlib
    
    try:
        # Create a safe temporary filename for processing
        original_path = Path(audio_path)
        safe_filename = f"temp_audio_{hashlib.md5(str(original_path).encode()).hexdigest()[:8]}{original_path.suffix}"
        safe_path = original_path.parent / safe_filename
        
        # Copy to safe filename if original has special characters or non-ASCII chars
        filename = str(original_path.name)
        has_korean = any('\uac00' <= char <= '\ud7af' for char in filename)
        has_special = any(char in filename for char in [' ', '(', ')', '[', ']', '&', '$', '!', '@', '#', '%'])
        needs_rename = has_korean or has_special
        
        if needs_rename:
            logger.debug(f"Renaming file for safe processing: {original_path.name} -> {safe_filename}")
            import shutil
            shutil.copy2(audio_path, safe_path)
            working_path = str(safe_path)
        else:
            working_path = audio_path
        
        # Get audio duration using ffprobe (faster than loading entire file)
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', 
            '-show_format', '-show_streams', working_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, check=True)
        info = json.loads(result.stdout)
        
        duration_seconds = float(info['format']['duration'])
        file_size_mb = os.path.getsize(working_path) / (1024 * 1024)
        
        logger.info(f"Original file: {file_size_mb:.1f}MB, {duration_seconds/60:.1f}min")
        
        # If file is already small enough, return original file
        if file_size_mb <= max_chunk_size_mb:
            logger.info("File size within limit, no splitting needed")
            # Clean up temporary file if created
            if needs_rename and safe_path.exists():
                safe_path.unlink()
            return [audio_path]
        
        # Calculate number of chunks needed
        num_chunks = int((file_size_mb / max_chunk_size_mb) + 0.5)
        chunk_duration = duration_seconds / num_chunks
        
        logger.info(f"Splitting into {num_chunks} chunks of ~{chunk_duration/60:.1f} minutes each")
        
        # Detect original file format for chunk export
        original_ext = Path(working_path).suffix.lower()
        chunk_format = "m4a" if original_ext == ".m4a" else "mp3"

        # Create temporary directory for chunks
        temp_dir = tempfile.mkdtemp()
        # Use safe name for chunk files (avoid Korean characters)
        safe_base_name = Path(working_path).stem  # Use the already safe filename
        chunks = []
        
        # Split audio using ffmpeg directly (much faster)
        with tqdm(total=num_chunks, desc="Splitting audio", unit="chunk") as pbar:
            for i in range(num_chunks):
                start_time = i * chunk_duration
                chunk_path = os.path.join(temp_dir, f"{safe_base_name}_chunk_{i+1}.{chunk_format}")
                
                # Use ffmpeg to extract chunk directly (no memory loading)
                # Optimize parameter order: seek before input for better performance
                cmd = [
                    'ffmpeg', '-y', 
                    '-ss', str(start_time),  # Seek before input for efficiency
                    '-i', working_path,
                    '-t', str(round(chunk_duration, 2)),  # Round to avoid precision issues
                    '-c', 'copy',  # Copy codec without re-encoding when possible
                    '-avoid_negative_ts', 'make_zero',
                    chunk_path
                ]
                
                try:
                    logger.debug(f"Running ffmpeg command: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, check=True, timeout=120)
                    
                    # Check if chunk was created successfully
                    if os.path.exists(chunk_path):
                        chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)
                        chunks.append(chunk_path)
                        logger.debug(f"Created chunk {i+1}: {Path(chunk_path).name} ({chunk_size_mb:.1f} MB)")
                    else:
                        logger.warning(f"Chunk {i+1} was not created successfully")
                        
                except subprocess.TimeoutExpired as e:
                    logger.error(f"Chunk {i+1} ffmpeg timeout after 60s")
                    continue
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to create chunk {i+1}: {e}")
                    logger.debug(f"ffmpeg stderr: {e.stderr}")
                    logger.debug(f"ffmpeg stdout: {e.stdout}")
                    continue
                
                pbar.update(1)
                pbar.set_postfix(chunk=f"{i+1}/{num_chunks}")

        logger.info(f"Split audio into {len(chunks)} chunks of max {max_chunk_size_mb} MB each")
        
        # Clean up temporary safe file if created
        if needs_rename and safe_path.exists():
            logger.debug(f"Cleaning up temporary file: {safe_filename}")
            safe_path.unlink()
            
        return chunks

    except Exception as e:
        logger.error(f"Error occurred during audio splitting: {e}, cause: {e.__cause__ or 'unknown'}")
        logger.debug(f"Audio splitting detailed error: {type(e).__name__}: {str(e)}")
        if e.__cause__:
            logger.debug(f"Audio splitting root cause: {type(e).__cause__.__name__}: {str(e.__cause__)}")
        
        # Clean up temporary safe file if created
        try:
            if 'needs_rename' in locals() and needs_rename and 'safe_path' in locals() and safe_path.exists():
                logger.debug(f"Cleaning up temporary file after error: {safe_path}")
                safe_path.unlink()
        except Exception as cleanup_error:
            logger.debug(f"Failed to cleanup temporary file: {cleanup_error}")
            
        # Return empty list to indicate failure, not the original file
        return []
