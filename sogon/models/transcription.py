"""
Transcription-related domain models
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class TranscriptionWord:
    """Represents a single word in transcription with timing"""
    
    word: str
    start: float
    end: float
    confidence: Optional[float] = None
    
    @property
    def duration(self) -> float:
        """Word duration in seconds"""
        return self.end - self.start
    
    def adjust_timing(self, offset_seconds: float) -> 'TranscriptionWord':
        """
        Create new word with adjusted timing
        
        Args:
            offset_seconds: Time offset to add
            
        Returns:
            TranscriptionWord: New word with adjusted timing
        """
        return TranscriptionWord(
            word=self.word,
            start=self.start + offset_seconds,
            end=self.end + offset_seconds,
            confidence=self.confidence
        )
    
    def __str__(self) -> str:
        return f"'{self.word}' ({self.start:.2f}-{self.end:.2f}s)"


@dataclass
class TranscriptionSegment:
    """Represents a segment of transcription with timing and metadata"""
    
    id: int
    text: str
    start: float
    end: float
    words: List[TranscriptionWord] = field(default_factory=list)
    confidence: Optional[float] = None
    language: Optional[str] = None
    
    @property
    def duration(self) -> float:
        """Segment duration in seconds"""
        return self.end - self.start
    
    @property
    def word_count(self) -> int:
        """Number of words in segment"""
        return len(self.words)
    
    @property
    def average_confidence(self) -> Optional[float]:
        """Average confidence of all words"""
        if not self.words:
            return self.confidence
        
        confidences = [w.confidence for w in self.words if w.confidence is not None]
        if not confidences:
            return self.confidence
        
        return sum(confidences) / len(confidences)
    
    def adjust_timing(self, offset_seconds: float) -> 'TranscriptionSegment':
        """
        Create new segment with adjusted timing
        
        Args:
            offset_seconds: Time offset to add
            
        Returns:
            TranscriptionSegment: New segment with adjusted timing
        """
        adjusted_words = [word.adjust_timing(offset_seconds) for word in self.words]
        
        return TranscriptionSegment(
            id=self.id,
            text=self.text,
            start=self.start + offset_seconds,
            end=self.end + offset_seconds,
            words=adjusted_words,
            confidence=self.confidence,
            language=self.language
        )
    
    def to_srt_format(self, segment_number: int) -> str:
        """
        Convert segment to SRT format
        
        Args:
            segment_number: Segment number for SRT
            
        Returns:
            str: SRT formatted segment
        """
        def seconds_to_srt_time(seconds: float) -> str:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        
        start_time = seconds_to_srt_time(self.start)
        end_time = seconds_to_srt_time(self.end)
        
        return f"{segment_number}\n{start_time} --> {end_time}\n{self.text}\n"
    
    def to_vtt_format(self) -> str:
        """
        Convert segment to VTT format
        
        Returns:
            str: VTT formatted segment
        """
        def seconds_to_vtt_time(seconds: float) -> str:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
        
        start_time = seconds_to_vtt_time(self.start)
        end_time = seconds_to_vtt_time(self.end)
        
        return f"{start_time} --> {end_time}\n{self.text}\n"
    
    def __str__(self) -> str:
        return f"Segment {self.id}: '{self.text[:50]}...' ({self.start:.2f}-{self.end:.2f}s)"


@dataclass
class TranscriptionResult:
    """Complete transcription result with metadata"""
    
    text: str
    language: str
    duration: float
    segments: List[TranscriptionSegment] = field(default_factory=list)
    words: List[TranscriptionWord] = field(default_factory=list)
    chunk_number: Optional[int] = None
    total_chunks: Optional[int] = None
    chunk_start_time: float = 0.0
    confidence: Optional[float] = None
    model_used: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def word_count(self) -> int:
        """Total number of words"""
        return len(self.words) if self.words else len(self.text.split())
    
    @property
    def segment_count(self) -> int:
        """Total number of segments"""
        return len(self.segments)
    
    @property
    def average_confidence(self) -> Optional[float]:
        """Average confidence score"""
        if self.confidence is not None:
            return self.confidence
        
        if self.segments:
            confidences = [s.average_confidence for s in self.segments 
                          if s.average_confidence is not None]
            if confidences:
                return sum(confidences) / len(confidences)
        
        return None
    
    @property
    def is_chunk(self) -> bool:
        """Check if this is a chunk result"""
        return self.chunk_number is not None
    
    def adjust_timing(self, offset_seconds: float) -> 'TranscriptionResult':
        """
        Create new result with adjusted timing for all segments and words
        
        Args:
            offset_seconds: Time offset to add
            
        Returns:
            TranscriptionResult: New result with adjusted timing
        """
        adjusted_segments = [seg.adjust_timing(offset_seconds) for seg in self.segments]
        adjusted_words = [word.adjust_timing(offset_seconds) for word in self.words]
        
        return TranscriptionResult(
            text=self.text,
            language=self.language,
            duration=self.duration,
            segments=adjusted_segments,
            words=adjusted_words,
            chunk_number=self.chunk_number,
            total_chunks=self.total_chunks,
            chunk_start_time=self.chunk_start_time + offset_seconds,
            confidence=self.confidence,
            model_used=self.model_used,
            created_at=self.created_at
        )
    
    def to_srt(self) -> str:
        """
        Convert to SRT format
        
        Returns:
            str: Complete SRT formatted text
        """
        if not self.segments:
            return ""
        
        srt_parts = []
        for i, segment in enumerate(self.segments, 1):
            srt_parts.append(segment.to_srt_format(i))
        
        return "\n".join(srt_parts)
    
    def to_vtt(self) -> str:
        """
        Convert to VTT format
        
        Returns:
            str: Complete VTT formatted text
        """
        if not self.segments:
            return "WEBVTT\n\n"
        
        vtt_parts = ["WEBVTT\n"]
        for segment in self.segments:
            vtt_parts.append(segment.to_vtt_format())
        
        return "\n".join(vtt_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization
        
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            "text": self.text,
            "language": self.language,
            "duration": self.duration,
            "segments": [
                {
                    "id": seg.id,
                    "text": seg.text,
                    "start": seg.start,
                    "end": seg.end,
                    "words": [
                        {
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "confidence": word.confidence
                        }
                        for word in seg.words
                    ],
                    "confidence": seg.confidence,
                    "language": seg.language
                }
                for seg in self.segments
            ],
            "words": [
                {
                    "word": word.word,
                    "start": word.start,
                    "end": word.end,
                    "confidence": word.confidence
                }
                for word in self.words
            ],
            "chunk_number": self.chunk_number,
            "total_chunks": self.total_chunks,
            "chunk_start_time": self.chunk_start_time,
            "confidence": self.confidence,
            "model_used": self.model_used,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def __str__(self) -> str:
        chunk_info = f" (chunk {self.chunk_number}/{self.total_chunks})" if self.is_chunk else ""
        return f"TranscriptionResult({len(self.text)} chars, {self.segment_count} segments, {self.language}{chunk_info})"


@dataclass
class CombinedTranscriptionResult:
    """Combined result from multiple transcription chunks"""
    
    text: str
    language: str
    total_duration: float
    chunk_results: List[TranscriptionResult] = field(default_factory=list)
    combined_segments: List[TranscriptionSegment] = field(default_factory=list)
    combined_words: List[TranscriptionWord] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total_chunks(self) -> int:
        """Total number of chunks processed"""
        return len(self.chunk_results)
    
    @property
    def total_word_count(self) -> int:
        """Total word count across all chunks"""
        return len(self.combined_words) if self.combined_words else len(self.text.split())
    
    @property
    def total_segment_count(self) -> int:
        """Total segment count across all chunks"""
        return len(self.combined_segments)
    
    @property
    def average_confidence(self) -> Optional[float]:
        """Average confidence across all chunks"""
        confidences = [chunk.average_confidence for chunk in self.chunk_results 
                      if chunk.average_confidence is not None]
        if not confidences:
            return None
        return sum(confidences) / len(confidences)
    
    def to_srt(self) -> str:
        """Convert combined result to SRT format"""
        if not self.combined_segments:
            return ""
        
        srt_parts = []
        for i, segment in enumerate(self.combined_segments, 1):
            srt_parts.append(segment.to_srt_format(i))
        
        return "\n".join(srt_parts)
    
    def to_vtt(self) -> str:
        """Convert combined result to VTT format"""
        if not self.combined_segments:
            return "WEBVTT\n\n"
        
        vtt_parts = ["WEBVTT\n"]
        for segment in self.combined_segments:
            vtt_parts.append(segment.to_vtt_format())
        
        return "\n".join(vtt_parts)
    
    def __str__(self) -> str:
        return f"CombinedTranscriptionResult({len(self.text)} chars, {self.total_chunks} chunks, {self.language})"