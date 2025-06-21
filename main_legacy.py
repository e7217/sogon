#!/usr/bin/env python3
"""
SOGON - Subtitle generator from YouTube URLs or local audio files
Supports both YouTube video processing and local audio file transcription
"""

import sys
import json
import logging
from logging.handlers import RotatingFileHandler
import argparse
from sogon import process_input_to_subtitle

# Logging configuration
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

file_handler = RotatingFileHandler('sogon.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s')
file_handler.setFormatter(file_formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)
root_logger.setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


def show_preview(file_path, title, max_chars=500):
    """File content preview"""
    logger.debug(f"show_preview called: file_path={file_path}, title={title}, max_chars={max_chars}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()[:max_chars]
            logger.info(f"\n=== {title} ===")
            logger.info(content)
            if len(content) == max_chars:
                logger.info("...")
                logger.debug(f"File content limited to {max_chars} characters")
    except FileNotFoundError as e:
        logger.error(f"File not found: {file_path}, cause: {e}")
    except Exception as e:
        logger.error(f"File preview error: {e}, cause: {e.__cause__ or 'unknown'}")
        logger.debug(f"File preview detailed error: {type(e).__name__}: {str(e)}")


def show_metadata_info(metadata_path):
    """Display metadata information"""
    logger.debug(f"show_metadata_info called: metadata_path={metadata_path}")
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            logger.info("\n=== Metadata Information ===")
            logger.info(f"Total chunks: {len(metadata)}")
            if metadata:
                first_chunk = metadata[0]
                logger.info(f"Language: {first_chunk.get('language', 'N/A')}")
                logger.info(f"Total duration: {first_chunk.get('duration', 'N/A')} seconds")
                if first_chunk.get("segments"):
                    segment_count = len(first_chunk['segments'])
                    logger.info(f"Number of segments: {segment_count}")
                    logger.debug(f"First chunk segment details: {first_chunk.get('segments')[:3] if segment_count > 3 else first_chunk.get('segments')}")
            else:
                logger.warning("Metadata is empty")
    except FileNotFoundError as e:
        logger.error(f"Metadata file not found: {metadata_path}, cause: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Metadata JSON parsing error: {e}, file: {metadata_path}, position: {e.pos if hasattr(e, 'pos') else 'unknown'}")
        logger.debug(f"JSON parsing detailed error: {type(e).__name__}: {str(e)}")
    except Exception as e:
        logger.error(f"Metadata display error: {e}, cause: {e.__cause__ or 'unknown'}")
        logger.debug(f"Metadata detailed error: {type(e).__name__}: {str(e)}")


def main():
    """Main execution function"""
    logger.debug("Main function started")
    logger.info("SOGON - Subtitle Generator")
    logger.info("Supports YouTube URLs and local audio files")
    logger.info("=" * 50)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="SOGON - Subtitle generator from YouTube URLs or local audio files")
    parser.add_argument("input_path", nargs="?", help="YouTube URL or audio file path")
    parser.add_argument("--format", "-f", choices=["txt", "srt", "json"], default="txt", 
                       help="Output format for subtitles (default: txt)")
    parser.add_argument("--output", "-o", default="./result", 
                       help="Base output directory (default: ./result)")
    parser.add_argument("--no-correction", action="store_true", 
                       help="Disable text correction")
    parser.add_argument("--no-ai-correction", action="store_true", 
                       help="Disable AI-based correction")
    parser.add_argument("--keep-audio", action="store_true", 
                       help="Keep downloaded audio files after processing")
    
    args = parser.parse_args()
    
    # Get input path
    if args.input_path:
        input_path = args.input_path
        logger.debug(f"Input received from command line: {input_path}")
    else:
        # Get URL or file path input from user
        logger.debug("Waiting for user input...")
        input_path = input("Enter YouTube URL or audio file path: ").strip()
        logger.debug(f"Input entered by user: {input_path}")

    # Exit with error message if no input provided
    if not input_path:
        logger.error("Error: YouTube URL or file path was not provided.")
        parser.print_help()
        logger.debug("Program terminated due to empty input")
        return

    # Subtitle format
    subtitle_format = args.format
    logger.debug(f"Subtitle format set: {subtitle_format}")

    # Base output directory (actual output created in date/time/title folder)
    base_output_dir = args.output
    logger.debug(f"Base output directory: {base_output_dir}")

    # Correction feature settings
    enable_correction = not args.no_correction
    use_ai_correction = not args.no_ai_correction
    keep_audio = args.keep_audio
    logger.debug(f"Correction settings: enable_correction={enable_correction}, use_ai_correction={use_ai_correction}")
    logger.debug(f"Keep audio files: {keep_audio}")

    logger.info("\nStarting subtitle generation...")
    logger.info(f"Input: {input_path}")
    logger.info(f"Format: {subtitle_format.upper()}")
    logger.info(f"Base output directory: {base_output_dir}")
    logger.info(f"Text correction: {'enabled' if enable_correction else 'disabled'}")
    logger.info(f"AI correction: {'enabled' if use_ai_correction else 'disabled'}")
    logger.info(f"Keep audio files: {'enabled' if keep_audio else 'disabled'}")
    logger.info("-" * 50)

    try:
        # Generate subtitles (including correction features)
        original_files, corrected_files, actual_output_dir = process_input_to_subtitle(
            input_path, base_output_dir, subtitle_format, enable_correction, use_ai_correction, keep_audio
        )

        logger.info(f"\n📁 Actual output directory: {actual_output_dir}")

        if original_files:
            subtitle_path, metadata_path, timestamp_path = original_files
            logger.info("\n✅ Subtitle generation completed!")
            logger.info(f"Original subtitle file: {subtitle_path}")
            logger.info(f"Original metadata file: {metadata_path}")
            logger.info(f"Original timestamp file: {timestamp_path}")
            logger.debug(f"Original files created: subtitle={subtitle_path}, metadata={metadata_path}, timestamp={timestamp_path}")

            if corrected_files:
                (
                    corrected_subtitle_path,
                    corrected_metadata_path,
                    corrected_timestamp_path,
                ) = corrected_files
                logger.info(f"\n📝 Corrected subtitle file: {corrected_subtitle_path}")
                logger.info(f"📝 Corrected metadata file: {corrected_metadata_path}")
                logger.info(f"📝 Corrected timestamp file: {corrected_timestamp_path}")
                logger.debug(f"Corrected files created: subtitle={corrected_subtitle_path}, metadata={corrected_metadata_path}, timestamp={corrected_timestamp_path}")
            else:
                logger.warning("Corrected files were not generated")

            # Result preview
            logger.debug("Starting result preview")
            show_preview(subtitle_path, "Original Subtitle Preview")

            if corrected_files:
                show_preview(corrected_subtitle_path, "Corrected Subtitle Preview")
            else:
                logger.debug("Skipping preview as no corrected files available")

            show_metadata_info(metadata_path)

        else:
            logger.error("Subtitle generation failed.")

    except Exception as e:
        logger.error(f"Error: {e}, cause: {e.__cause__ or 'unknown'}")
        logger.debug(f"Exception details: {type(e).__name__}: {str(e)}")
        import traceback
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        if e.__cause__:
            logger.debug(f"Root cause: {type(e.__cause__).__name__}: {str(e.__cause__)}")


if __name__ == "__main__":
    logger.debug("Program started")
    main()
    logger.debug("Program terminated")
