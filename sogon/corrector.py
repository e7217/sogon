"""
Text correction module
"""

import os
import re
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


def fix_ai_based_corrections(text, api_key=None, base_url="https://api.openai.com/v1", model="gpt-4o-mini", temperature=0.1):
    """
    AI-based text post-processing and correction

    Args:
        text (str): Original text
        api_key (str): OpenAI API key
        base_url (str): API base URL
        model (str): Model to use for correction
        temperature (float): Temperature for generation

    Returns:
        str: Corrected text
    """
    logger.debug(f"AI correction started: text length={len(text)}, api_key provided={api_key is not None}")
    
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        logger.debug("API key retrieved from environment variable")

    if not api_key:
        logger.warning("No API key available for AI-based correction. Returning original text.")
        logger.debug("Returning original text due to missing API key")
        return text

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        # Split text into chunks if too long
        max_chunk_length = 1500

        logger.info(f"Original text length: {len(text)} characters")

        chunks = _split_text_into_chunks(text, max_chunk_length)

        logger.info(f"Text split into {len(chunks)} chunks")

        corrected_chunks = []

        for i, chunk in enumerate(chunks):
            logger.info(f"AI correction in progress... ({i + 1}/{len(chunks)}) - chunk length: {len(chunk)}")
            logger.debug(f"Chunk {i+1} content preview: {chunk[:50]}...")

            if not chunk.strip():
                logger.warning(f"Chunk {i+1} is empty, skipping")
                continue

            prompt = f"""The following is text converted from Korean speech recognition. 
Please naturally correct errors that may occur during speech recognition:

1. Correct misrecognized technical terms or proper nouns
2. Naturally correct grammatically awkward parts
3. Correct words or phrases that don't make sense
4. Correct to match the overall context
5. Maintain the original meaning and length as much as possible

Original text:
{chunk}

Please output only the corrected text (without explanations or additional descriptions):"""

            logger.debug(f"Starting OpenAI API call for chunk {i+1}")
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a Korean text correction expert. You should naturally correct speech recognition errors while maintaining the original meaning and length as much as possible.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                    max_tokens=3000,
                )
                logger.debug(f"Chunk {i+1} API call successful")
            except Exception as api_error:
                logger.error(f"Chunk {i+1} API call failed: {api_error}, cause: {api_error.__cause__ or 'unknown'}")
                logger.debug(f"Chunk {i+1} API error details: {type(api_error).__name__}: {str(api_error)}")
                corrected_chunks.append(chunk)  # Use original chunk
                continue

            corrected_chunk = response.choices[0].message.content.strip()
            logger.info(f"Chunk {i + 1} correction completed: {len(corrected_chunk)} characters")

            if corrected_chunk:
                corrected_chunks.append(corrected_chunk)
                logger.debug(f"Chunk {i+1} correction result preview: {corrected_chunk[:50]}...")
            else:
                logger.warning(f"Chunk {i+1} correction result is empty")

        final_result = " ".join(corrected_chunks)
        logger.info(f"Final corrected text length: {len(final_result)} characters")
        logger.debug(f"Final result preview: {final_result[:100]}...")
        
        # Calculate correction ratio
        if len(text) > 0:
            improvement_ratio = len(final_result) / len(text)
            logger.debug(f"Correction ratio: {improvement_ratio:.2f} (original: {len(text)}, corrected: {len(final_result)})")
            if improvement_ratio < 0.5:
                logger.warning(f"Corrected text is less than 50% of original ({improvement_ratio:.2f})")

        return final_result

    except Exception as e:
        logger.error(f"Error occurred during AI-based correction: {e}, cause: {e.__cause__ or 'unknown'}")
        logger.debug(f"AI correction detailed error: {type(e).__name__}: {str(e)}")
        if e.__cause__:
            logger.debug(f"AI correction root cause: {type(e.__cause__).__name__}: {str(e.__cause__)}")
        return text


def format_timestamp(seconds):
    """
    Convert seconds to HH:mm:ss.SSS format
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    milliseconds = int((secs % 1) * 1000)
    secs = int(secs)

    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def parse_timestamp(timestamp_str):
    """
    Convert timestamp string to seconds
    """
    try:
        parts = timestamp_str.split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        result = hours * 3600 + minutes * 60 + seconds
        logger.debug(f"Timestamp parsing: {timestamp_str} -> {result} seconds")
        return result
    except (ValueError, IndexError) as e:
        logger.warning(f"Timestamp parsing failed: {timestamp_str}, error: {e}, cause: {e.__cause__ or 'unknown'}")
        logger.debug(f"Timestamp parsing detailed error: {type(e).__name__}: {str(e)}")
        return 0.0


def sort_timestamps_and_fix_overlaps(timestamps_data):
    """
    Sort timestamps chronologically and fix overlapping parts
    """
    logger.debug(f"Starting timestamp sorting: {len(timestamps_data)} items")
    # Sort by start time
    sorted_data = sorted(timestamps_data, key=lambda x: parse_timestamp(x[0]))
    logger.debug("Timestamp sorting completed")

    # Fix overlapping time intervals
    fixed_data = []
    for i, (start, end, text) in enumerate(sorted_data):
        start_seconds = parse_timestamp(start)
        end_seconds = parse_timestamp(end)

        # Check if overlapping with previous segment
        if fixed_data and start_seconds < parse_timestamp(fixed_data[-1][1]):
            logger.debug(f"Segment {i+1} overlap detected: {start} < {fixed_data[-1][1]}")
            adjusted_start = fixed_data[-1][1]
            if end_seconds <= parse_timestamp(adjusted_start):
                end_seconds = parse_timestamp(adjusted_start) + 1.0
                adjusted_end = format_timestamp(end_seconds)
                logger.debug(f"Segment {i+1} end time adjusted: {end} -> {adjusted_end}")
            else:
                adjusted_end = end

            fixed_data.append((adjusted_start, adjusted_end, text))
        else:
            fixed_data.append((start, end, text))

    logger.debug(f"Timestamp overlap correction completed: {len(fixed_data)} items")
    return fixed_data


def correct_transcription_text(text, metadata, api_key=None, use_ai=True, base_url="https://api.openai.com/v1", model="gpt-4o-mini", temperature=0.1):
    """
    Correct transcribed text using AI
    """
    logger.debug(f"correct_transcription_text called: use_ai={use_ai}, metadata_chunks={len(metadata) if metadata else 0}")
    logger.info("Starting text correction...")
    logger.info(f"Original text length: {len(text)} characters")
    logger.info(f"Original text preview: {text[:100]}...")

    corrected_text = text

    # AI-based correction
    if use_ai:
        logger.info("AI-based text correction...")
        ai_corrected_text = fix_ai_based_corrections(text, api_key, base_url, model, temperature)

        # Use AI correction result only if it's 50% or more of original
        if ai_corrected_text and len(ai_corrected_text.strip()) > len(text) * 0.5:
            corrected_text = ai_corrected_text
            logger.info(f"AI correction completed: {len(corrected_text)} characters")
            quality_ratio = len(ai_corrected_text.strip()) / len(text)
            logger.debug(f"AI correction quality ratio: {quality_ratio:.2f}")
        else:
            logger.warning("AI correction result too short - using original text.")
            if ai_corrected_text:
                logger.debug(f"AI correction result length: {len(ai_corrected_text.strip())}, original length: {len(text)}, ratio: {len(ai_corrected_text.strip()) / len(text):.2f}")
            else:
                logger.debug("AI correction result is None or empty")

    # Clean up timestamp data
    logger.info("Sorting and correcting timestamps...")
    logger.debug(f"Number of metadata chunks: {len(metadata)}")
    corrected_metadata = []

    for idx, chunk in enumerate(metadata):
        corrected_chunk = _process_metadata_chunk(chunk, idx)
        corrected_metadata.append(corrected_chunk)

    logger.info("Text correction completed!")
    logger.debug(f"Correction completed: text length={len(corrected_text)}, metadata chunks={len(corrected_metadata)}")
    return corrected_text, corrected_metadata


def _split_text_into_chunks(text: str, max_chunk_length: int) -> list:
    """Split text into chunks with reduced nesting complexity"""
    if len(text) <= max_chunk_length:
        logger.debug("Text is within maximum length, no splitting needed")
        return [text]

    logger.debug(f"Text exceeds maximum length ({max_chunk_length}), starting split")
    
    # Try different splitting strategies
    sentences = _try_split_strategies(text)
    chunks = _build_chunks_from_sentences(sentences, max_chunk_length)
    
    logger.debug(f"Split completed: {len(chunks)} chunks created")
    return chunks


def _try_split_strategies(text: str) -> list:
    """Try different text splitting strategies in order of preference"""
    strategies = [
        lambda t: re.split(r"[.!?]\s*", t),  # Sentences
        lambda t: re.split(r",\s*", t),      # Phrases
        lambda t: t.split(" ")               # Words
    ]
    
    for strategy in strategies:
        result = strategy(text)
        if len(result) > 1:
            return result
    
    return [text]  # Fallback


def _build_chunks_from_sentences(sentences: list, max_length: int) -> list:
    """Build chunks from sentences with word-level fallback"""
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        if _can_add_to_chunk(current_chunk, sentence, max_length):
            current_chunk = _add_to_chunk(current_chunk, sentence)
        else:
            if current_chunk:
                chunks.append(current_chunk)
            
            current_chunk = _handle_long_sentence(sentence, max_length, chunks)
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def _can_add_to_chunk(current_chunk: str, sentence: str, max_length: int) -> bool:
    """Check if sentence can be added to current chunk"""
    test_chunk = current_chunk + (" " if current_chunk else "") + sentence
    return len(test_chunk) <= max_length


def _add_to_chunk(current_chunk: str, sentence: str) -> str:
    """Add sentence to current chunk"""
    return current_chunk + (" " if current_chunk else "") + sentence


def _handle_long_sentence(sentence: str, max_length: int, chunks: list) -> str:
    """Handle sentences that are longer than max_length"""
    if len(sentence) <= max_length:
        return sentence
    
    # Split long sentence by words
    words = sentence.split(" ")
    temp_chunk = ""
    
    for word in words:
        if len(temp_chunk + " " + word) <= max_length:
            temp_chunk += (" " if temp_chunk else "") + word
        else:
            if temp_chunk:
                chunks.append(temp_chunk)
            temp_chunk = word
    
    return temp_chunk


def _process_metadata_chunk(chunk: dict, idx: int) -> dict:
    """Process a single metadata chunk with reduced nesting"""
    segments = chunk.get("segments", [])
    logger.debug(f"Processing chunk {idx+1}: segments={len(segments)}")
    
    # Extract timestamp data
    timestamps_data = _extract_timestamp_data(segments)
    
    # Sort timestamps and fix overlaps
    logger.debug(f"Chunk {idx+1} timestamp data count: {len(timestamps_data)}")
    fixed_timestamps = sort_timestamps_and_fix_overlaps(timestamps_data)
    
    if len(fixed_timestamps) != len(timestamps_data):
        logger.warning(f"Chunk {idx+1} timestamp count changed after correction: {len(timestamps_data)} -> {len(fixed_timestamps)}")
    
    # Create updated segments
    updated_segments = _create_updated_segments(fixed_timestamps)
    
    # Return updated chunk
    corrected_chunk = chunk.copy()
    corrected_chunk["segments"] = updated_segments
    return corrected_chunk


def _extract_timestamp_data(segments: list) -> list:
    """Extract timestamp data from segments"""
    timestamps_data = []
    
    for segment in segments:
        start_time = format_timestamp(segment.get("start", 0))
        end_time = format_timestamp(segment.get("end", 0))
        segment_text = segment.get("text", "").strip()
        
        if segment_text:
            timestamps_data.append((start_time, end_time, segment_text))
    
    return timestamps_data


def _create_updated_segments(fixed_timestamps: list) -> list:
    """Create updated segments from fixed timestamp data"""
    updated_segments = []
    
    for start_time, end_time, segment_text in fixed_timestamps:
        updated_segments.append({
            "start": parse_timestamp(start_time),
            "end": parse_timestamp(end_time),
            "text": segment_text,
        })
    
    return updated_segments
