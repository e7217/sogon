"""
Transcription service implementation
"""

import asyncio
import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor

from .interfaces import TranscriptionService
from ..models.audio import AudioFile, AudioChunk
from ..models.transcription import TranscriptionResult, TranscriptionSegment
from ..exceptions.transcription import TranscriptionError
from ..transcriber import transcribe_audio
from ..config import get_settings

logger = logging.getLogger(__name__)


class TranscriptionServiceImpl(TranscriptionService):
    """Implementation of TranscriptionService interface"""
    
    def __init__(self, api_key: str = None, max_workers: int = 4):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.groq_api_key
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def transcribe_audio(self, audio_file: AudioFile, source_language: str = None) -> TranscriptionResult:
        """Transcribe single audio file"""
        try:
            logger.info(f"Starting transcription for {audio_file.name}")
            
            # Run transcription in thread executor
            loop = asyncio.get_event_loop()
            text, metadata = await loop.run_in_executor(
                self.executor,
                self._transcribe_sync,
                str(audio_file.path),
                source_language
            )
            
            if not text:
                raise TranscriptionError("Transcription returned empty result")
            
            # Convert to domain model
            result = self._convert_to_transcription_result(text, metadata, audio_file)
            logger.info(f"Transcription completed: {len(text)} characters")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to transcribe {audio_file.path}: {e}")
            raise TranscriptionError(f"Transcription failed: {e}")
    
    async def transcribe_chunks(self, chunks: List[AudioChunk], source_language: str = None) -> List[TranscriptionResult]:
        """Transcribe multiple audio chunks"""
        try:
            logger.info(f"Starting transcription for {len(chunks)} chunks")
            
            # Create tasks for parallel transcription
            tasks = []
            for chunk in chunks:
                # Create AudioFile representation for chunk
                chunk_audio = AudioFile(
                    path=chunk.path,
                    duration_seconds=chunk.duration_seconds,
                    size_bytes=chunk.size_bytes,
                    format=chunk.parent_file.format
                )
                task = self.transcribe_audio(chunk_audio, source_language)
                tasks.append(task)
            
            # Wait for all transcriptions to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and log errors
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Chunk {i+1} transcription failed: {result}")
                    # Create empty result for failed chunk
                    chunk = chunks[i]
                    empty_result = TranscriptionResult(
                        text="",
                        segments=[],
                        language="unknown",
                        duration=chunk.duration_seconds,
                        chunk_number=chunk.chunk_number,
                        total_chunks=chunk.total_chunks,
                        chunk_start_time=chunk.start_time_seconds
                    )
                    valid_results.append(empty_result)
                else:
                    # Update chunk information
                    chunk = chunks[i]
                    result.chunk_number = chunk.chunk_number
                    result.total_chunks = chunk.total_chunks
                    result.chunk_start_time = chunk.start_time_seconds
                    valid_results.append(result)
            
            logger.info(f"Completed transcription for {len(valid_results)} chunks")
            return valid_results
            
        except Exception as e:
            logger.error(f"Failed to transcribe chunks: {e}")
            raise TranscriptionError(f"Chunk transcription failed: {e}")
    
    async def combine_transcriptions(self, results: List[TranscriptionResult]) -> TranscriptionResult:
        """Combine multiple transcription results"""
        try:
            if not results:
                raise TranscriptionError("No transcription results to combine")
            
            # Sort by chunk index to ensure correct order
            sorted_results = sorted(results, key=lambda r: r.chunk_number or 0)
            
            # Combine text
            combined_text = " ".join(result.text.strip() for result in sorted_results if result.text.strip())
            
            # Combine segments with time offset adjustment
            combined_segments = self._combine_segments_with_offset(sorted_results)
            
            # Calculate total duration
            total_duration = sum(result.duration for result in sorted_results)
            
            # Use language from first non-empty result
            language = next((r.language for r in sorted_results if r.language), "unknown")
            
            combined_result = TranscriptionResult(
                text=combined_text,
                segments=combined_segments,
                language=language,
                duration=total_duration,
                chunk_number=None,  # Combined result doesn't have chunk index
                total_chunks=len(sorted_results),
                chunk_start_time=0.0
            )
            
            logger.info(f"Combined {len(results)} transcription results into {len(combined_text)} characters")
            return combined_result
            
        except Exception as e:
            logger.error(f"Failed to combine transcription results: {e}")
            raise TranscriptionError(f"Failed to combine transcriptions: {e}")
    
    def _transcribe_sync(self, audio_path: str, source_language: str = None) -> tuple:
        """Synchronous transcription wrapper"""
        try:
            return transcribe_audio(audio_path, api_key=self.api_key, source_language=source_language)
        except Exception as e:
            logger.error(f"Synchronous transcription failed: {e}")
            return "", []
    
    def _convert_to_transcription_result(self, text: str, metadata: list, audio_file: AudioFile) -> TranscriptionResult:
        """Convert raw transcription output to domain model"""
        try:
            segments = []
            language = "unknown"
            
            # Extract segments from metadata
            segments, language = self._extract_segments_from_metadata(metadata)
            
            # Calculate duration from segments if available, otherwise use audio file duration
            duration = self._calculate_duration_from_segments(segments, audio_file.duration_seconds)
            
            return TranscriptionResult(
                text=text.strip(),
                segments=segments,
                language=language,
                duration=duration,
                chunk_number=None,
                total_chunks=1,
                chunk_start_time=0.0
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse transcription metadata: {e}")
            # Return basic result without segments
            return TranscriptionResult(
                text=text.strip(),
                segments=[],
                language="unknown",
                duration=audio_file.duration_seconds,
                chunk_number=None,
                total_chunks=1,
                chunk_start_time=0.0
            )
    
    def _calculate_duration_from_segments(self, segments: List[TranscriptionSegment], fallback_duration: float) -> float:
        """Calculate total duration from segments, with fallback"""
        if not segments:
            return fallback_duration
        
        # Find the maximum end time among all segments
        max_end_time = max(segment.end for segment in segments)
        
        # Use the larger of segment max_end_time or fallback_duration
        return max(max_end_time, fallback_duration)
    
    def _combine_segments_with_offset(self, sorted_results: List[TranscriptionResult]) -> List[TranscriptionSegment]:
        """Combine segments from multiple results with time offset adjustment"""
        combined_segments = []
        segment_id = 1
        
        for result in sorted_results:
            time_offset = result.chunk_start_time or 0
            for segment in result.segments:
                adjusted_segment = TranscriptionSegment(
                    id=segment_id,
                    start=segment.start + time_offset,
                    end=segment.end + time_offset,
                    text=segment.text,
                    confidence=segment.confidence
                )
                combined_segments.append(adjusted_segment)
                segment_id += 1
        
        return combined_segments
    
    def _extract_segments_from_metadata(self, metadata: list) -> tuple[List[TranscriptionSegment], str]:
        """Extract segments and language from metadata with reduced nesting"""
        segments = []
        language = "unknown"
        
        for chunk_meta in metadata:
            if not isinstance(chunk_meta, dict):
                continue
                
            # Extract language
            chunk_language = chunk_meta.get("language", "unknown")
            if chunk_language != "unknown":
                language = chunk_language
            
            # Extract segments
            chunk_segments = chunk_meta.get("segments", [])
            segments.extend(self._create_segments_from_chunk(chunk_segments, len(segments)))
        
        return segments, language
    
    def _create_segments_from_chunk(self, chunk_segments: list, start_id: int) -> List[TranscriptionSegment]:
        """Create TranscriptionSegment objects from chunk data"""
        segments = []
        
        for i, seg in enumerate(chunk_segments):
            if isinstance(seg, dict):
                segment = TranscriptionSegment(
                    id=start_id + i + 1,
                    start=seg.get("start", 0.0),
                    end=seg.get("end", 0.0),
                    text=seg.get("text", "").strip(),
                    confidence=seg.get("confidence", 0.0)
                )
                segments.append(segment)
        
        return segments
    
    def __del__(self):
        """Cleanup executor on deletion"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)