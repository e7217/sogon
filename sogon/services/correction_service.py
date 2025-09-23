"""
Text correction service implementation using OpenAI SDK
"""

import logging
from openai import OpenAI
from .interfaces import CorrectionService
from ..models.correction import CorrectionResult
from ..models.transcription import TranscriptionResult

logger = logging.getLogger(__name__)

class CorrectionServiceImpl(CorrectionService):
    """Implementation of CorrectionService interface using OpenAI SDK"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None, temperature: float = None):
        from ..config import get_settings
        settings = get_settings()

        # Use provided values or fall back to correction-specific settings
        self.api_key = api_key or settings.effective_correction_api_key
        self.base_url = base_url or settings.correction_base_url
        self.model = model or settings.correction_model
        self.temperature = temperature if temperature is not None else settings.correction_temperature

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=1200.0)
    
    async def correct_text(self, text: str, use_ai: bool = True) -> CorrectionResult:
        """Correct transcribed text using OpenAI"""
        if not use_ai:
            return CorrectionResult(
                original_text=text,
                corrected_text=text,
                corrections_made=[],
                confidence_score=1.0
            )
        
        try:
            prompt = f"""다음 음성인식 텍스트를 자연스럽게 교정해주세요. 원본의 의미와 길이를 최대한 유지하면서 음성인식 오류를 수정해주세요:

{text}

교정된 텍스트만 출력해주세요 (설명이나 추가 설명 없이):"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Korean text correction expert. You should naturally correct speech recognition errors while maintaining the original meaning and length as much as possible."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=3000
            )
            
            corrected_text = response.choices[0].message.content.strip()
            
            # Basic validation - use corrected text only if it's reasonable length
            if corrected_text and len(corrected_text.strip()) > len(text) * 0.5:
                return CorrectionResult(
                    original_text=text,
                    corrected_text=corrected_text,
                    corrections_made=[],  # Could be enhanced to track specific corrections
                    confidence_score=0.8
                )
            else:
                logger.warning("AI correction result too short - using original text")
                return CorrectionResult(
                    original_text=text,
                    corrected_text=text,
                    corrections_made=[],
                    confidence_score=1.0
                )
                
        except Exception as e:
            logger.error(f"Text correction failed: {e}")
            return CorrectionResult(
                original_text=text,
                corrected_text=text,
                corrections_made=[],
                confidence_score=1.0
            )
    
    async def correct_transcription(self, transcription: TranscriptionResult, use_ai: bool = True) -> TranscriptionResult:
        """Correct transcription with metadata preservation - placeholder implementation"""
        # This would implement transcription correction with metadata
        return transcription