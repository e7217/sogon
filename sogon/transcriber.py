"""
Audio transcription module
"""

import os
import logging
from groq import Groq
from .downloader import split_audio_by_size

logger = logging.getLogger(__name__)


def transcribe_audio(audio_file_path, api_key=None):
    """
    Convert audio file to text using Groq Whisper Turbo
    Large files are automatically split for processing

    Args:
        audio_file_path (str): Audio file path
        api_key (str): Groq API key (retrieved from environment variable if not provided)

    Returns:
        tuple: (converted text, metadata list)
    """
    logger.debug(f"transcribe_audio called: audio_file_path={audio_file_path}, api_key provided={api_key is not None}")
    
    # API key setup
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY")
        logger.debug("API key retrieved from environment variable")

    if not api_key:
        logger.error("GROQ_API_KEY is not set")
        raise ValueError(
            "Please set GROQ_API_KEY environment variable or provide api_key parameter."
        )

    # Initialize Groq client
    logger.debug("Initializing Groq client")
    client = Groq(api_key=api_key)

    try:
        # Check file size and split if necessary
        logger.debug(f"Starting audio file splitting: {audio_file_path}")
        audio_chunks = split_audio_by_size(audio_file_path)
        logger.info(f"Audio file split into {len(audio_chunks)} chunks")
        all_transcriptions = []
        all_metadata = []

        for i, chunk_path in enumerate(audio_chunks):
            logger.info(f"Processing chunk {i + 1}/{len(audio_chunks)}...")

            # Open audio file and convert
            logger.debug(f"Starting Whisper transcription for chunk {i+1}: {chunk_path}")
            try:
                with open(chunk_path, "rb") as audio_file:
                    response = client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-large-v3-turbo",
                        response_format="verbose_json",  # Include metadata
                        temperature=0.0,  # More consistent results
                    )
                logger.debug(f"Chunk {i+1} Whisper transcription successful")
            except Exception as api_error:
                logger.error(f"Chunk {i+1} Whisper transcription failed: {api_error}, cause: {api_error.__cause__ or 'unknown'}")
                logger.debug(f"Chunk {i+1} API error details: {type(api_error).__name__}: {str(api_error)}")
                continue

            # Separate text and metadata
            transcription_text = response.text
            logger.info(f"Chunk {i + 1} transcription result: {len(transcription_text)} characters")
            logger.info(f"Chunk {i + 1} preview: {transcription_text[:100]}...")
            
            if not transcription_text.strip():
                logger.warning(f"Chunk {i + 1} transcription result is empty")
            
            all_transcriptions.append(transcription_text)
            logger.debug(f"Chunk {i + 1} transcription text added successfully")

            # Collect metadata
            segments = getattr(response, "segments", [])
            words = getattr(response, "words", []) if hasattr(response, "words") else []
            
            metadata = {
                "chunk_number": i + 1,
                "total_chunks": len(audio_chunks),
                "language": getattr(response, "language", "auto"),
                "duration": getattr(response, "duration", None),
                "segments": segments,
                "words": words,
            }
            all_metadata.append(metadata)
            
            logger.debug(f"Chunk {i + 1} metadata: language={metadata['language']}, duration={metadata['duration']}, segments={len(segments)}, words={len(words)}")

            # Delete temporary chunk file (if not original)
            if chunk_path != audio_file_path:
                try:
                    os.remove(chunk_path)
                    logger.debug(f"Chunk {i + 1} temporary file deleted: {chunk_path}")
                except OSError as e:
                    logger.warning(f"Chunk {i + 1} temporary file deletion failed: {e}, cause: {e.__cause__ or 'unknown'}")
                    logger.debug(f"File deletion detailed error: {type(e).__name__}: {str(e)}")

        # Combine all transcription results
        combined_text = " ".join(all_transcriptions)
        logger.info(f"Transcription completed: total {len(combined_text)} characters")
        logger.info(f"Transcription result preview: {combined_text[:100]}...")
        
        # Check transcription quality
        if len(combined_text.strip()) == 0:
            logger.error("Transcription result is empty")
        elif len(combined_text) < 50:
            logger.warning(f"Transcription result too short: {len(combined_text)} characters")
        else:
            logger.debug(f"Transcription quality check passed: {len(combined_text)} characters")
        
        logger.debug(f"Return data: text length={len(combined_text)}, metadata chunks={len(all_metadata)}")
        return combined_text, all_metadata

    except Exception as e:
        logger.error(f"Error occurred during audio conversion: {e}, cause: {e.__cause__ or 'unknown'}")
        logger.debug(f"Exception details: {type(e).__name__}: {str(e)}")
        import traceback
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        if e.__cause__:
            logger.debug(f"Audio conversion root cause: {type(e.__cause__).__name__}: {str(e.__cause__)}")
        return None, None
