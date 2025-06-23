"""
File operations utility functions
"""

import os
import json
import re
import logging
from datetime import datetime
from ..corrector import format_timestamp, correct_transcription_text

logger = logging.getLogger(__name__)


def create_output_directory(base_dir="./result", video_title=None):
    """
    Create output directory in yyyyMMDD_HHmmss_title format
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if video_title:
        safe_title = re.sub(r'[<>:"/\\|?*]', "", video_title)[:50]
        folder_name = f"{timestamp}_{safe_title}"
    else:
        folder_name = timestamp

    output_dir = os.path.join(base_dir, folder_name)
    os.makedirs(output_dir, exist_ok=True)

    return output_dir


def extract_timestamps_and_text(metadata):
    """
    Extract timestamps and text from metadata
    """
    timestamps_data = []

    for chunk in metadata:
        segments = chunk.get("segments", [])
        for segment in segments:
            start_time = format_timestamp(segment.get("start", 0))
            end_time = format_timestamp(segment.get("end", 0))
            text = segment.get("text", "").strip()

            if text:
                timestamps_data.append((start_time, end_time, text))

    return timestamps_data


def save_subtitle_and_metadata(
    text,
    metadata,
    output_dir,
    base_filename,
    format="txt",
    correction_enabled=True,
    use_ai_correction=True,
    api_key=None,
):
    """
    Save subtitles and metadata to files (including correction features)
    """
    try:
        # Save original files first
        subtitle_path = os.path.join(output_dir, f"{base_filename}.{format}")
        metadata_path = os.path.join(output_dir, f"{base_filename}_metadata.json")
        timestamp_path = os.path.join(output_dir, f"{base_filename}_timestamps.txt")

        # Save original subtitles
        _save_subtitle_by_format(subtitle_path, text, metadata, format)

        # Save original metadata
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Save original timestamps
        timestamps_data = extract_timestamps_and_text(metadata)
        with open(timestamp_path, "w", encoding="utf-8") as f:
            f.write("Timestamped Subtitles\n")
            f.write("=" * 50 + "\n\n")
            for start_time, end_time, segment_text in timestamps_data:
                f.write(f"[{start_time} → {end_time}] {segment_text}\n")

        logger.info(f"Original subtitles saved: {subtitle_path}")
        logger.info(f"Original metadata saved: {metadata_path}")
        logger.info(f"Original timestamps saved: {timestamp_path}")

        corrected_files = None

        # If correction feature is enabled
        if correction_enabled:
            try:
                # Text correction
                corrected_text, corrected_metadata = correct_transcription_text(
                    text, metadata, api_key=api_key, use_ai=use_ai_correction
                )

                # Save corrected files
                corrected_subtitle_path = os.path.join(
                    output_dir, f"{base_filename}_corrected.{format}"
                )
                corrected_metadata_path = os.path.join(
                    output_dir, f"{base_filename}_corrected_metadata.json"
                )
                corrected_timestamp_path = os.path.join(
                    output_dir, f"{base_filename}_corrected_timestamps.txt"
                )

                # Save corrected subtitles
                _save_subtitle_by_format(corrected_subtitle_path, corrected_text, corrected_metadata, format)

                # Save corrected metadata
                with open(corrected_metadata_path, "w", encoding="utf-8") as f:
                    json.dump(corrected_metadata, f, indent=2, ensure_ascii=False)

                # Save corrected timestamps
                corrected_timestamps_data = extract_timestamps_and_text(
                    corrected_metadata
                )
                with open(corrected_timestamp_path, "w", encoding="utf-8") as f:
                    f.write("Timestamped Subtitles (Corrected)\n")
                    f.write("=" * 50 + "\n\n")
                    for (
                        start_time,
                        end_time,
                        corrected_segment_text,
                    ) in corrected_timestamps_data:
                        f.write(
                            f"[{start_time} → {end_time}] {corrected_segment_text}\n"
                        )

                corrected_files = (
                    corrected_subtitle_path,
                    corrected_metadata_path,
                    corrected_timestamp_path,
                )

                logger.info(f"Corrected subtitles saved: {corrected_subtitle_path}")
                logger.info(f"Corrected metadata saved: {corrected_metadata_path}")
                logger.info(f"Corrected timestamps saved: {corrected_timestamp_path}")

            except Exception as e:
                logger.error(f"Error occurred during text correction: {e}, cause: {e.__cause__ or 'unknown'}")
                logger.debug(f"Text correction detailed error: {type(e).__name__}: {str(e)}")
                if e.__cause__:
                    logger.debug(f"Text correction root cause: {type(e.__cause__).__name__}: {str(e.__cause__)}")
                logger.warning("Only original files will be saved.")

        return subtitle_path, metadata_path, timestamp_path, corrected_files

    except Exception as e:
        logger.error(f"Error occurred during file saving: {e}, cause: {e.__cause__ or 'unknown'}")
        logger.debug(f"File saving detailed error: {type(e).__name__}: {str(e)}")
        if e.__cause__:
            logger.debug(f"File saving root cause: {type(e.__cause__).__name__}: {str(e.__cause__)}")
        return None, None, None, None


def _save_subtitle_by_format(file_path: str, text: str, metadata: list, format: str) -> None:
    """Save subtitle in specified format with reduced if/elif nesting"""
    
    format_handlers = {
        "txt": _save_txt_format,
        "srt": _save_srt_format,
        "vtt": _save_vtt_format,
        "json": _save_json_format
    }
    
    handler = format_handlers.get(format)
    if handler:
        handler(file_path, text, metadata)
    else:
        raise ValueError(f"Unsupported format: {format}")


def _save_txt_format(file_path: str, text: str, metadata: list) -> None:
    """Save as plain text format"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)


def _save_srt_format(file_path: str, text: str, metadata: list) -> None:
    """Save as SRT format with proper timestamps"""
    try:
        timestamps_data = extract_timestamps_and_text(metadata)
        
        with open(file_path, "w", encoding="utf-8") as f:
            if timestamps_data:
                # Generate proper SRT with timestamps
                for i, (start_time, end_time, segment_text) in enumerate(timestamps_data, 1):
                    # Convert seconds to SRT time format (HH:MM:SS,mmm)
                    start_srt = _seconds_to_srt_time(start_time)
                    end_srt = _seconds_to_srt_time(end_time)
                    
                    f.write(f"{i}\n")
                    f.write(f"{start_srt} --> {end_srt}\n")
                    f.write(f"{segment_text.strip()}\n\n")
            else:
                # Fallback: single subtitle block
                f.write("1\n")
                f.write("00:00:00,000 --> 99:59:59,999\n")
                f.write(text)
                f.write("\n")
    except Exception as e:
        logger.warning(f"Failed to generate timestamped SRT, using fallback: {e}")
        # Fallback to simple format
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("1\n")
            f.write("00:00:00,000 --> 99:59:59,999\n")
            f.write(text)
            f.write("\n")


def _save_vtt_format(file_path: str, text: str, metadata: list) -> None:
    """Save as VTT format with proper timestamps"""
    try:
        timestamps_data = extract_timestamps_and_text(metadata)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            
            if timestamps_data:
                # Generate proper VTT with timestamps
                for start_time, end_time, segment_text in timestamps_data:
                    # Convert seconds to VTT time format (HH:MM:SS.mmm)
                    start_vtt = _seconds_to_vtt_time(start_time)
                    end_vtt = _seconds_to_vtt_time(end_time)
                    
                    f.write(f"{start_vtt} --> {end_vtt}\n")
                    f.write(f"{segment_text.strip()}\n\n")
            else:
                # Fallback: single subtitle block
                f.write("00:00:00.000 --> 99:59:59.999\n")
                f.write(text)
                f.write("\n")
    except Exception as e:
        logger.warning(f"Failed to generate timestamped VTT, using fallback: {e}")
        # Fallback to simple format
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            f.write("00:00:00.000 --> 99:59:59.999\n")
            f.write(text)
            f.write("\n")


def _save_json_format(file_path: str, text: str, metadata: list) -> None:
    """Save as JSON format"""
    timestamps_data = extract_timestamps_and_text(metadata)
    json_data = {
        "text": text,
        "segments": [
            {
                "start_time": start_time,
                "end_time": end_time,
                "text": segment_text
            }
            for start_time, end_time, segment_text in timestamps_data
        ]
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)


def _seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def _seconds_to_vtt_time(seconds: float) -> str:
    """Convert seconds to VTT time format (HH:MM:SS.mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

