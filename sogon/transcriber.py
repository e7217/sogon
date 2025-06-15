"""
Audio transcription module
"""

import os
import logging
from groq import Groq
from tqdm import tqdm
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
        
        if not audio_chunks:
            logger.error("Audio file splitting failed. Unable to process audio file.")
            return "", []
            
        logger.info(f"Audio file split into {len(audio_chunks)} chunks")
        all_transcriptions = []
        all_metadata = []

        # Calculate chunk start times for timestamp offset
        # Load each chunk to get actual durations (not assuming equal duration)
        chunk_start_times = []
        if len(audio_chunks) > 1:
            from pydub import AudioSegment
            current_time_seconds = 0.0
            estimated_chunk_duration = None  # Cache estimated duration for reuse
            
            for i, chunk_path in enumerate(audio_chunks):
                chunk_start_times.append(current_time_seconds)
                
                # Load each chunk to get its actual duration
                try:
                    chunk_audio = AudioSegment.from_file(chunk_path)
                    chunk_duration_seconds = len(chunk_audio) / 1000.0
                    current_time_seconds += chunk_duration_seconds
                    logger.debug(f"Chunk {i+1} duration: {chunk_duration_seconds:.2f}s, starts at: {chunk_start_times[i]:.2f}s")
                except Exception as e:
                    logger.warning(f"Could not load chunk {i+1} for duration calculation: {e}")
                    # Fallback: estimate based on equal division
                    if estimated_chunk_duration is None:
                        # Calculate estimated duration only once
                        try:
                            full_audio = AudioSegment.from_file(audio_file_path)
                            estimated_chunk_duration = len(full_audio) / len(audio_chunks) / 1000.0
                            logger.debug(f"Calculated estimated chunk duration: {estimated_chunk_duration:.2f}s")
                        except Exception:
                            logger.warning("Could not estimate chunk duration, using default")
                            estimated_chunk_duration = 60.0  # Default 1 minute per chunk
                    
                    current_time_seconds += estimated_chunk_duration
                    logger.debug(f"Using estimated duration for chunk {i+1}: {estimated_chunk_duration:.2f}s")
        else:
            chunk_start_times = [0.0]
            
        logger.info(f"Chunk start times: {[f'{t:.1f}s' for t in chunk_start_times]}")

        with tqdm(total=len(audio_chunks), desc="Transcribing chunks", unit="chunk") as pbar:
            for i, chunk_path in enumerate(audio_chunks):
                logger.info(f"Processing chunk {i + 1}/{len(audio_chunks)}...")
                pbar.set_description(f"Transcribing chunk {i + 1}/{len(audio_chunks)}")
                
                chunk_start_time = chunk_start_times[i]

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

                # Collect metadata and adjust timestamps
                segments = getattr(response, "segments", [])
                words = getattr(response, "words", []) if hasattr(response, "words") else []
                
                # Adjust segment timestamps with chunk offset
                adjusted_segments = []
                for segment in segments:
                    # Safely convert to dictionary for consistent handling
                    adjusted_segment = None
                    try:
                        if hasattr(segment, '__dict__'):
                            # Object with attributes - convert to dict
                            adjusted_segment = vars(segment).copy()
                        elif hasattr(segment, 'copy') and callable(getattr(segment, 'copy', None)):
                            # Dictionary or dict-like object with copy method
                            adjusted_segment = segment.copy()
                        elif hasattr(segment, '__getitem__') and hasattr(segment, 'keys'):
                            # Dict-like object without copy method
                            adjusted_segment = dict(segment)
                        else:
                            # Fallback to dict conversion
                            adjusted_segment = dict(segment)
                    except (TypeError, ValueError, AttributeError) as e:
                        logger.warning(f"Could not convert segment to dict: {e}, creating empty dict")
                        adjusted_segment = {}
                    
                    # Safely extract timestamps - check both attribute and key access
                    start_time = None
                    end_time = None
                    
                    # Try attribute access first
                    try:
                        if hasattr(segment, 'start'):
                            start_time = segment.start
                        if hasattr(segment, 'end'):
                            end_time = segment.end
                    except AttributeError:
                        pass
                    
                    # Try key access only if object supports it
                    if start_time is None or end_time is None:
                        try:
                            # Check if object supports 'in' operator safely
                            if hasattr(segment, '__contains__'):
                                if start_time is None and 'start' in segment:
                                    start_time = segment['start']
                                if end_time is None and 'end' in segment:
                                    end_time = segment['end']
                        except (TypeError, KeyError):
                            pass
                    
                    # Apply timestamp adjustments
                    if start_time is not None:
                        adjusted_segment['start'] = start_time + chunk_start_time
                    if end_time is not None:
                        adjusted_segment['end'] = end_time + chunk_start_time
                        
                    adjusted_segments.append(adjusted_segment)
                
                # Adjust word timestamps with chunk offset
                adjusted_words = []
                for word in words:
                    # Safely convert to dictionary for consistent handling
                    adjusted_word = None
                    try:
                        if hasattr(word, '__dict__'):
                            # Object with attributes - convert to dict
                            adjusted_word = vars(word).copy()
                        elif hasattr(word, 'copy') and callable(getattr(word, 'copy', None)):
                            # Dictionary or dict-like object with copy method
                            adjusted_word = word.copy()
                        elif hasattr(word, '__getitem__') and hasattr(word, 'keys'):
                            # Dict-like object without copy method
                            adjusted_word = dict(word)
                        else:
                            # Fallback to dict conversion
                            adjusted_word = dict(word)
                    except (TypeError, ValueError, AttributeError) as e:
                        logger.warning(f"Could not convert word to dict: {e}, creating empty dict")
                        adjusted_word = {}
                    
                    # Safely extract timestamps - check both attribute and key access
                    start_time = None
                    end_time = None
                    
                    # Try attribute access first
                    try:
                        if hasattr(word, 'start'):
                            start_time = word.start
                        if hasattr(word, 'end'):
                            end_time = word.end
                    except AttributeError:
                        pass
                    
                    # Try key access only if object supports it
                    if start_time is None or end_time is None:
                        try:
                            # Check if object supports 'in' operator safely
                            if hasattr(word, '__contains__'):
                                if start_time is None and 'start' in word:
                                    start_time = word['start']
                                if end_time is None and 'end' in word:
                                    end_time = word['end']
                        except (TypeError, KeyError):
                            pass
                    
                    # Apply timestamp adjustments
                    if start_time is not None:
                        adjusted_word['start'] = start_time + chunk_start_time
                    if end_time is not None:
                        adjusted_word['end'] = end_time + chunk_start_time
                        
                    adjusted_words.append(adjusted_word)
                
                metadata = {
                    "chunk_number": i + 1,
                    "total_chunks": len(audio_chunks),
                    "chunk_start_time": chunk_start_time,
                    "language": getattr(response, "language", "auto"),
                    "duration": getattr(response, "duration", None),
                    "segments": adjusted_segments,
                    "words": adjusted_words,
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
                
                # Update progress bar
                pbar.update(1)
                if transcription_text:
                    pbar.set_postfix(chars=len(transcription_text))

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
