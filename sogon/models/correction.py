"""
Text correction domain models
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class CorrectionType(Enum):
    """Types of corrections that can be applied"""
    
    SPELLING = "spelling"
    GRAMMAR = "grammar"
    PUNCTUATION = "punctuation"
    CAPITALIZATION = "capitalization"
    SPACING = "spacing"
    WORD_BOUNDARY = "word_boundary"
    AI_ENHANCEMENT = "ai_enhancement"
    CUSTOM = "custom"


@dataclass
class CorrectionChange:
    """Represents a single correction change"""
    
    original_text: str
    corrected_text: str
    start_position: int
    end_position: int
    correction_type: CorrectionType
    confidence: Optional[float] = None
    reason: Optional[str] = None
    
    @property
    def is_deletion(self) -> bool:
        """Check if this is a deletion"""
        return len(self.corrected_text) == 0
    
    @property
    def is_insertion(self) -> bool:
        """Check if this is an insertion"""
        return len(self.original_text) == 0
    
    @property
    def is_replacement(self) -> bool:
        """Check if this is a replacement"""
        return len(self.original_text) > 0 and len(self.corrected_text) > 0
    
    @property
    def change_length(self) -> int:
        """Get the length difference caused by this change"""
        return len(self.corrected_text) - len(self.original_text)
    
    def __str__(self) -> str:
        return f"{self.correction_type.value}: '{self.original_text}' → '{self.corrected_text}'"


@dataclass
class CorrectionResult:
    """Result of text correction with detailed changes"""
    
    original_text: str
    corrected_text: str
    changes: List[CorrectionChange] = field(default_factory=list)
    correction_method: str = "unknown"
    model_used: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_changes(self) -> bool:
        """Check if any changes were made"""
        return len(self.changes) > 0
    
    @property
    def change_count(self) -> int:
        """Total number of changes"""
        return len(self.changes)
    
    @property
    def correction_types_used(self) -> List[CorrectionType]:
        """List of correction types that were applied"""
        return list(set(change.correction_type for change in self.changes))
    
    @property
    def character_change_count(self) -> int:
        """Total character changes (insertions + deletions)"""
        return sum(abs(change.change_length) for change in self.changes)
    
    @property
    def improvement_ratio(self) -> float:
        """Ratio of text that was improved (0.0 to 1.0)"""
        if not self.original_text:
            return 0.0
        return self.character_change_count / len(self.original_text)
    
    def get_changes_by_type(self, correction_type: CorrectionType) -> List[CorrectionChange]:
        """Get all changes of a specific type"""
        return [change for change in self.changes if change.correction_type == correction_type]
    
    def get_high_confidence_changes(self, threshold: float = 0.8) -> List[CorrectionChange]:
        """Get changes with confidence above threshold"""
        return [
            change for change in self.changes 
            if change.confidence is not None and change.confidence >= threshold
        ]
    
    def apply_changes_to_text(self, text: str) -> str:
        """
        Apply all changes to the given text
        
        Args:
            text: Text to apply changes to
            
        Returns:
            str: Text with changes applied
        """
        if not self.changes:
            return text
        
        # Sort changes by position (reverse order to maintain positions)
        sorted_changes = sorted(self.changes, key=lambda c: c.start_position, reverse=True)
        
        result = text
        for change in sorted_changes:
            result = (
                result[:change.start_position] + 
                change.corrected_text + 
                result[change.end_position:]
            )
        
        return result
    
    def generate_diff_report(self) -> str:
        """
        Generate a human-readable diff report
        
        Returns:
            str: Formatted diff report
        """
        if not self.has_changes:
            return "No changes were made."
        
        lines = [
            f"Correction Report - {self.change_count} changes made",
            f"Method: {self.correction_method}",
            f"Processing time: {self.processing_time_seconds:.2f}s" if self.processing_time_seconds else "",
            "",
            "Changes:"
        ]
        
        for i, change in enumerate(self.changes, 1):
            confidence_str = f" (confidence: {change.confidence:.2f})" if change.confidence else ""
            reason_str = f" - {change.reason}" if change.reason else ""
            
            lines.append(f"{i}. {change}{confidence_str}{reason_str}")
        
        return "\n".join(filter(None, lines))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "original_text": self.original_text,
            "corrected_text": self.corrected_text,
            "changes": [
                {
                    "original_text": change.original_text,
                    "corrected_text": change.corrected_text,
                    "start_position": change.start_position,
                    "end_position": change.end_position,
                    "correction_type": change.correction_type.value,
                    "confidence": change.confidence,
                    "reason": change.reason
                }
                for change in self.changes
            ],
            "correction_method": self.correction_method,
            "model_used": self.model_used,
            "processing_time_seconds": self.processing_time_seconds,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "has_changes": self.has_changes,
            "change_count": self.change_count,
            "character_change_count": self.character_change_count,
            "improvement_ratio": self.improvement_ratio
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CorrectionResult':
        """Create CorrectionResult from dictionary"""
        changes = []
        for change_data in data.get("changes", []):
            change = CorrectionChange(
                original_text=change_data["original_text"],
                corrected_text=change_data["corrected_text"],
                start_position=change_data["start_position"],
                end_position=change_data["end_position"],
                correction_type=CorrectionType(change_data["correction_type"]),
                confidence=change_data.get("confidence"),
                reason=change_data.get("reason")
            )
            changes.append(change)
        
        result = cls(
            original_text=data["original_text"],
            corrected_text=data["corrected_text"],
            changes=changes,
            correction_method=data.get("correction_method", "unknown"),
            model_used=data.get("model_used"),
            processing_time_seconds=data.get("processing_time_seconds"),
            metadata=data.get("metadata", {})
        )
        
        if data.get("created_at"):
            result.created_at = datetime.fromisoformat(data["created_at"])
        
        return result
    
    def __str__(self) -> str:
        change_summary = f"{self.change_count} changes" if self.has_changes else "no changes"
        return f"CorrectionResult({change_summary}, method: {self.correction_method})"


@dataclass
class CorrectionStats:
    """Statistics about correction operations"""
    
    total_corrections: int = 0
    correction_type_counts: Dict[CorrectionType, int] = field(default_factory=dict)
    total_processing_time: float = 0.0
    average_confidence: Optional[float] = None
    total_character_changes: int = 0
    
    def add_result(self, result: CorrectionResult) -> None:
        """Add a correction result to the statistics"""
        self.total_corrections += 1
        
        if result.processing_time_seconds:
            self.total_processing_time += result.processing_time_seconds
        
        self.total_character_changes += result.character_change_count
        
        # Count correction types
        for change in result.changes:
            self.correction_type_counts[change.correction_type] = (
                self.correction_type_counts.get(change.correction_type, 0) + 1
            )
        
        # Update average confidence
        confidences = [
            change.confidence for change in result.changes 
            if change.confidence is not None
        ]
        if confidences:
            if self.average_confidence is None:
                self.average_confidence = sum(confidences) / len(confidences)
            else:
                # Running average
                total_confidences = self.total_corrections - 1
                self.average_confidence = (
                    (self.average_confidence * total_confidences + sum(confidences) / len(confidences)) /
                    self.total_corrections
                )
    
    @property
    def average_processing_time(self) -> float:
        """Average processing time per correction"""
        if self.total_corrections == 0:
            return 0.0
        return self.total_processing_time / self.total_corrections
    
    @property
    def most_common_correction_type(self) -> Optional[CorrectionType]:
        """Most frequently used correction type"""
        if not self.correction_type_counts:
            return None
        return max(self.correction_type_counts, key=self.correction_type_counts.get)
    
    def __str__(self) -> str:
        return f"CorrectionStats({self.total_corrections} corrections, avg time: {self.average_processing_time:.2f}s)"