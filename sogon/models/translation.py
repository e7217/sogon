"""
Translation domain models
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class SupportedLanguage(Enum):
    """Supported languages for translation"""
    
    KOREAN = "ko"
    ENGLISH = "en"
    JAPANESE = "ja"
    CHINESE_SIMPLIFIED = "zh-cn"
    CHINESE_TRADITIONAL = "zh-tw"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    ARABIC = "ar"
    HINDI = "hi"
    THAI = "th"
    VIETNAMESE = "vi"
    
    @property
    def display_name(self) -> str:
        """Get display name for the language"""
        display_names = {
            "ko": "한국어",
            "en": "English", 
            "ja": "日本語",
            "zh-cn": "中文(简体)",
            "zh-tw": "中文(繁體)",
            "es": "Español",
            "fr": "Français", 
            "de": "Deutsch",
            "it": "Italiano",
            "pt": "Português",
            "ru": "Русский",
            "ar": "العربية",
            "hi": "हिन्दी",
            "th": "ไทย",
            "vi": "Tiếng Việt"
        }
        return display_names.get(self.value, self.value)


@dataclass
class TranslationSegment:
    """A single translation segment with timestamp"""
    
    start_time: float
    end_time: float
    original_text: str
    translated_text: str
    confidence_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "confidence_score": self.confidence_score
        }


@dataclass
class TranslationResult:
    """Result of text translation with metadata"""
    
    original_text: str
    translated_text: str
    source_language: str
    target_language: SupportedLanguage
    segments: List[TranslationSegment] = field(default_factory=list)
    confidence_score: Optional[float] = None
    model_used: Optional[str] = None
    processing_time: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def word_count(self) -> int:
        """Get word count of original text"""
        return len(self.original_text.split())
    
    @property
    def character_count(self) -> int:
        """Get character count of original text"""
        return len(self.original_text)
    
    @property
    def has_segments(self) -> bool:
        """Check if translation has timestamped segments"""
        return len(self.segments) > 0
    
    def get_segment_by_time(self, timestamp: float) -> Optional[TranslationSegment]:
        """Get segment that contains the given timestamp"""
        for segment in self.segments:
            if segment.start_time <= timestamp <= segment.end_time:
                return segment
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "source_language": self.source_language,
            "target_language": self.target_language.value,
            "target_language_display": self.target_language.display_name,
            "segments": [segment.to_dict() for segment in self.segments],
            "confidence_score": self.confidence_score,
            "model_used": self.model_used,
            "processing_time": self.processing_time,
            "word_count": self.word_count,
            "character_count": self.character_count,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranslationResult':
        """Create from dictionary"""
        segments = [
            TranslationSegment(
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                original_text=seg["original_text"],
                translated_text=seg["translated_text"],
                confidence_score=seg.get("confidence_score")
            )
            for seg in data.get("segments", [])
        ]
        
        result = cls(
            original_text=data["original_text"],
            translated_text=data["translated_text"],
            source_language=data["source_language"],
            target_language=SupportedLanguage(data["target_language"]),
            segments=segments,
            confidence_score=data.get("confidence_score"),
            model_used=data.get("model_used"),
            processing_time=data.get("processing_time"),
            metadata=data.get("metadata", {})
        )
        
        if data.get("created_at"):
            result.created_at = datetime.fromisoformat(data["created_at"])
        
        return result
    
    def to_srt(self) -> str:
        """Convert translation to SRT format"""
        if not self.segments:
            # If no segments, create a single subtitle for entire content
            return f"1\n00:00:00,000 --> 99:59:59,999\n{self.translated_text}\n"
        
        srt_lines = []
        for i, segment in enumerate(self.segments, 1):
            start_time = self._format_srt_time(segment.start_time)
            end_time = self._format_srt_time(segment.end_time)
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(segment.translated_text)
            srt_lines.append("")  # Empty line between segments
        
        return "\n".join(srt_lines)
    
    def to_vtt(self) -> str:
        """Convert translation to WebVTT format"""
        vtt_lines = ["WEBVTT", ""]
        
        if not self.segments:
            # If no segments, create a single subtitle for entire content
            vtt_lines.extend([
                "00:00:00.000 --> 99:59:59.999",
                self.translated_text,
                ""
            ])
            return "\n".join(vtt_lines)
        
        for segment in self.segments:
            start_time = self._format_vtt_time(segment.start_time)
            end_time = self._format_vtt_time(segment.end_time)
            vtt_lines.append(f"{start_time} --> {end_time}")
            vtt_lines.append(segment.translated_text)
            vtt_lines.append("")  # Empty line between segments
        
        return "\n".join(vtt_lines)
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds to SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def _format_vtt_time(self, seconds: float) -> str:
        """Format seconds to WebVTT time format (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
    
    def __str__(self) -> str:
        lang_info = f"{self.source_language} → {self.target_language.display_name}"
        return f"Translation ({lang_info}): {len(self.translated_text)} chars"


@dataclass
class TranslationRequest:
    """Request for translation with configuration"""
    
    text: str
    target_language: SupportedLanguage
    source_language: Optional[str] = None  # Auto-detect if None
    preserve_formatting: bool = True
    include_segments: bool = True
    model_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "text": self.text,
            "target_language": self.target_language.value,
            "source_language": self.source_language,
            "preserve_formatting": self.preserve_formatting,
            "include_segments": self.include_segments,
            "model_name": self.model_name
        }