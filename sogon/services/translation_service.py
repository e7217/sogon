"""
Translation service implementation using LLM
"""

import logging
import time
from typing import List, Optional
import groq
from groq import Groq

from .interfaces import TranslationService
from ..models.translation import TranslationResult, TranslationRequest, SupportedLanguage, TranslationSegment
from ..models.transcription import TranscriptionResult
from ..exceptions.base import SogonError

logger = logging.getLogger(__name__)


class TranslationError(SogonError):
    """Translation specific error"""
    pass


class TranslationServiceImpl(TranslationService):
    """Implementation of TranslationService using Groq LLM"""
    
    def __init__(self, api_key: str, model: str = "llama-3.1-70b-versatile"):
        self.client = Groq(api_key=api_key)
        self.model = model
        self.supported_languages = list(SupportedLanguage)
    
    async def translate_text(
        self, 
        text: str, 
        target_language: SupportedLanguage
    ) -> TranslationResult:
        """Translate plain text"""
        try:
            start_time = time.time()
            
            # Auto-detect source language
            source_language = await self.detect_language(text)
            
            # Create translation prompt
            prompt = self._create_translation_prompt(text, target_language, source_language)
            
            # Call LLM for translation
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            translated_text = response.choices[0].message.content.strip()
            processing_time = time.time() - start_time
            
            # Create result
            result = TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=source_language,
                target_language=target_language,
                model_used=self.model,
                processing_time=processing_time
            )
            
            logger.info(f"Translation completed: {source_language} → {target_language.value} ({len(text)} chars in {processing_time:.2f}s)")
            return result
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise TranslationError(f"Translation failed: {e}")
    
    async def translate_transcription(
        self, 
        transcription: TranscriptionResult, 
        target_language: SupportedLanguage
    ) -> TranslationResult:
        """Translate transcription with metadata preservation"""
        try:
            start_time = time.time()
            
            # Auto-detect source language
            source_language = await self.detect_language(transcription.text)
            
            # Translate segments individually to preserve timestamps
            translated_segments = []
            
            if transcription.segments:
                for segment in transcription.segments:
                    if segment.text.strip():
                        segment_translation = await self.translate_text(
                            segment.text, target_language
                        )
                        
                        translated_segment = TranslationSegment(
                            start_time=segment.start,
                            end_time=segment.end,
                            original_text=segment.text,
                            translated_text=segment_translation.translated_text,
                            confidence_score=segment.confidence
                        )
                        translated_segments.append(translated_segment)
            
            # Translate full text for completeness
            full_translation = await self.translate_text(
                transcription.text, target_language
            )
            
            processing_time = time.time() - start_time
            
            # Create result with segments
            result = TranslationResult(
                original_text=transcription.text,
                translated_text=full_translation.translated_text,
                source_language=source_language,
                target_language=target_language,
                segments=translated_segments,
                model_used=self.model,
                processing_time=processing_time,
                metadata={
                    "original_transcription_id": getattr(transcription, 'id', None),
                    "original_language": transcription.language,
                    "original_duration": transcription.duration
                }
            )
            
            logger.info(f"Transcription translation completed: {len(translated_segments)} segments, {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Transcription translation failed: {e}")
            raise TranslationError(f"Transcription translation failed: {e}")
    
    async def translate_request(self, request: TranslationRequest) -> TranslationResult:
        """Process translation request"""
        return await self.translate_text(
            request.text,
            request.target_language
        )
    
    async def detect_language(self, text: str) -> str:
        """Detect source language of text"""
        try:
            # Use a simple prompt for language detection
            prompt = f"""Detect the language of the following text and respond with only the ISO 639-1 language code (e.g., 'en', 'ko', 'ja', 'zh'):

{text[:500]}"""  # Limit text length for detection
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a language detection system. Respond only with the ISO 639-1 language code."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            detected_language = response.choices[0].message.content.strip().lower()
            
            # Validate detected language
            valid_codes = ["en", "ko", "ja", "zh", "es", "fr", "de", "it", "pt", "ru", "ar", "hi", "th", "vi"]
            if detected_language not in valid_codes:
                logger.warning(f"Unknown language detected: {detected_language}, defaulting to 'en'")
                return "en"
            
            logger.info(f"Language detected: {detected_language}")
            return detected_language
            
        except Exception as e:
            logger.warning(f"Language detection failed: {e}, defaulting to 'en'")
            return "en"
    
    def get_supported_languages(self) -> List[SupportedLanguage]:
        """Get list of supported languages"""
        return self.supported_languages
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for translation"""
        return """You are a professional translator. Your task is to translate text accurately while preserving:
1. The original meaning and context
2. Natural flow and readability in the target language
3. Technical terms and proper nouns appropriately
4. Formatting and structure where possible

Provide only the translated text without any additional comments or explanations."""
    
    def _create_translation_prompt(
        self, 
        text: str, 
        target_language: SupportedLanguage, 
        source_language: str
    ) -> str:
        """Create translation prompt"""
        source_lang_name = self._get_language_name(source_language)
        target_lang_name = target_language.display_name
        
        return f"""Translate the following text from {source_lang_name} to {target_lang_name}:

{text}"""
    
    def _get_language_name(self, language_code: str) -> str:
        """Get display name for language code"""
        language_names = {
            "en": "English",
            "ko": "Korean",
            "ja": "Japanese", 
            "zh": "Chinese",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ar": "Arabic",
            "hi": "Hindi",
            "th": "Thai",
            "vi": "Vietnamese"
        }
        return language_names.get(language_code, language_code.capitalize())