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

    def __init__(self, max_workers: int = 4, provider=None):
        """
        Initialize transcription service.

        Args:
            max_workers: Maximum number of concurrent transcription workers
            provider: TranscriptionProvider instance, or None for API-based providers
        """
        self.settings = get_settings()
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.provider = provider

        # API key for legacy API-based providers (when provider is None)
        self.api_key = self.settings.effective_transcription_api_key
    
    async def transcribe_audio(self, audio_file: AudioFile, source_language: str = None, model: str = None, base_url: str = None) -> TranscriptionResult:
        """
        Transcribe single audio file.

        Args:
            audio_file: Audio file to transcribe
            source_language: Source language hint for transcription
            model: Model name override (API-based providers only)
            base_url: Base URL override (API-based providers only)

        Returns:
            TranscriptionResult containing text and metadata
        """
        try:
            logger.info(f"Starting transcription for {audio_file.name}")

            # Provider-based transcription (e.g., stable-whisper)
            if self.provider:
                logger.info(f"Using provider: {self.provider.provider_name}")

                # Call provider.transcribe() with audio_file
                # Note: config parameter not used yet (will be added in future task)
                provider_result = await self.provider.transcribe(audio_file, config=None)

                # Convert provider result to TranscriptionResult
                # Provider returns mock object with: text, segments, language, duration
                result = self._convert_provider_result_to_transcription_result(
                    provider_result, audio_file
                )
                logger.info(f"Provider transcription completed: {len(result.text)} characters")
                return result

            # Legacy API-based flow (openai, groq)
            # Run transcription in thread executor
            loop = asyncio.get_event_loop()
            text, metadata = await loop.run_in_executor(
                self.executor,
                self._transcribe_sync,
                str(audio_file.path),
                source_language,
                model,
                base_url
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
    
    async def transcribe_chunks(self, chunks: List[AudioChunk], source_language: str = None, model: str = None, base_url: str = None) -> List[TranscriptionResult]:
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
                task = self.transcribe_audio(chunk_audio, source_language, model, base_url)
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
    
    def _transcribe_sync(self, audio_path: str, source_language: str = None, model: str = None, base_url: str = None) -> tuple:
        """Synchronous transcription wrapper"""
        try:
            # Use new transcription settings with fallbacks
            effective_model = model or self.settings.transcription_model
            effective_base_url = base_url or self.settings.transcription_base_url

            return transcribe_audio(
                audio_path,
                api_key=self.api_key,
                source_language=source_language,
                model=effective_model,
                base_url=effective_base_url
            )
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

    def _convert_provider_result_to_transcription_result(self, provider_result, audio_file: AudioFile) -> TranscriptionResult:
        """Convert provider result to TranscriptionResult domain model (Task 25)"""
        try:
            # Provider returns object with: text, segments (list of dicts), language, duration
            segments = []

            # Convert dict segments to TranscriptionSegment objects
            if hasattr(provider_result, 'segments'):
                for i, seg_dict in enumerate(provider_result.segments):
                    segment = TranscriptionSegment(
                        id=i + 1,
                        start=seg_dict.get("start", 0.0),
                        end=seg_dict.get("end", 0.0),
                        text=seg_dict.get("text", "").strip(),
                        confidence=seg_dict.get("confidence", 0.0)
                    )
                    segments.append(segment)

            # Extract duration from provider result or use audio file duration
            duration = getattr(provider_result, 'duration', None) or audio_file.duration_seconds

            return TranscriptionResult(
                text=getattr(provider_result, 'text', '').strip(),
                segments=segments,
                language=getattr(provider_result, 'language', 'unknown'),
                duration=duration,
                chunk_number=None,
                total_chunks=1,
                chunk_start_time=0.0
            )

        except Exception as e:
            logger.warning(f"Failed to convert provider result: {e}")
            # Return basic result with text only
            return TranscriptionResult(
                text=getattr(provider_result, 'text', '').strip(),
                segments=[],
                language=getattr(provider_result, 'language', 'unknown'),
                duration=audio_file.duration_seconds,
                chunk_number=None,
                total_chunks=1,
                chunk_start_time=0.0
            )

    def __del__(self):
        """Cleanup executor on deletion"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)