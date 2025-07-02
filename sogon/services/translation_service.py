"""
Translation service implementation using LLM
"""

import asyncio
import logging
import time
from typing import List
from openai import AsyncOpenAI

from .interfaces import TranslationService
from ..models.translation import TranslationResult, TranslationRequest, SupportedLanguage, TranslationSegment
from ..models.transcription import TranscriptionResult
from ..exceptions.base import SogonError

logger = logging.getLogger(__name__)


class TranslationError(SogonError):
    """Translation specific error"""
    pass


class TranslationServiceImpl(TranslationService):
    """Implementation of TranslationService using OpenAI SDK"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o-mini", temperature: float = 0.3, max_concurrent_requests: int = 10):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        self.max_concurrent_requests = max_concurrent_requests
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
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
            async with self.semaphore:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
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
    
    async def translate_batch(
        self, 
        texts: List[str], 
        target_language: SupportedLanguage,
        source_language: str = None,
        chunk_size: int = None
    ) -> List[TranslationResult]:
        """Translate multiple texts concurrently with chunking support"""
        if not texts:
            return []
        
        # Auto-detect source language from first text if not provided
        if not source_language:
            source_language = await self.detect_language(texts[0])
        
        # Use default chunk size if not provided (2x concurrent requests for better throughput)
        if chunk_size is None:
            chunk_size = self.max_concurrent_requests * 2
        
        # Process in chunks if the batch is large
        if len(texts) > chunk_size:
            logger.info(f"Large batch detected ({len(texts)} texts), processing in chunks of {chunk_size}")
            return await self._translate_large_batch(texts, target_language, source_language, chunk_size)
        
        # Process normal-sized batch
        return await self._translate_chunk(texts, target_language, source_language)
    
    async def _translate_large_batch(
        self, 
        texts: List[str], 
        target_language: SupportedLanguage,
        source_language: str,
        chunk_size: int
    ) -> List[TranslationResult]:
        """Process large batch in chunks"""
        all_results = []
        total_chunks = (len(texts) + chunk_size - 1) // chunk_size
        
        for i in range(0, len(texts), chunk_size):
            chunk = texts[i:i + chunk_size]
            chunk_num = (i // chunk_size) + 1
            
            logger.info(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} texts)")
            
            chunk_results = await self._translate_chunk(chunk, target_language, source_language)
            all_results.extend(chunk_results)
            
            # Small delay between chunks to avoid overwhelming the API
            if chunk_num < total_chunks:
                await asyncio.sleep(0.1)
        
        return all_results
    
    async def _translate_chunk(
        self, 
        texts: List[str], 
        target_language: SupportedLanguage,
        source_language: str
    ) -> List[TranslationResult]:
        """Translate a single chunk of texts"""
        start_time = time.time()
        
        # Create translation tasks
        tasks = []
        for text in texts:
            if text.strip():
                task = self._translate_single_text(text, target_language, source_language)
                tasks.append(task)
            else:
                # Handle empty text
                tasks.append(asyncio.create_task(self._create_empty_result(text, target_language, source_language)))
        
        # Execute all translations concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        translation_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Translation failed for text {i}: {result}")
                # Create fallback result
                fallback_result = TranslationResult(
                    original_text=texts[i],
                    translated_text=texts[i],  # Fallback to original
                    source_language=source_language,
                    target_language=target_language,
                    model_used=self.model,
                    metadata={"error": str(result)}
                )
                translation_results.append(fallback_result)
            else:
                translation_results.append(result)
        
        chunk_time = time.time() - start_time
        total_chars = sum(len(text) for text in texts)
        logger.info(f"Chunk translation completed: {len(texts)} texts, {total_chars} chars in {chunk_time:.2f}s (avg: {chunk_time/len(texts):.2f}s per text)")
        
        return translation_results
    
    async def _translate_single_text(
        self, 
        text: str, 
        target_language: SupportedLanguage, 
        source_language: str,
        max_retries: int = 3
    ) -> TranslationResult:
        """Internal method for single text translation with retry logic"""
        start_time = time.time()
        
        # Create translation prompt
        prompt = self._create_translation_prompt(text, target_language, source_language)
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # Call LLM for translation with semaphore
                async with self.semaphore:
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": self._get_system_prompt()},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=self.temperature,
                        max_tokens=4000
                    )
                
                translated_text = response.choices[0].message.content.strip()
                processing_time = time.time() - start_time
                
                return TranslationResult(
                    original_text=text,
                    translated_text=translated_text,
                    source_language=source_language,
                    target_language=target_language,
                    model_used=self.model,
                    processing_time=processing_time
                )
                
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = (2 ** attempt) * 0.5  # Exponential backoff: 0.5, 1, 2 seconds
                    logger.warning(f"Translation attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Translation failed after {max_retries + 1} attempts: {e}")
                    raise last_exception
    
    async def _create_empty_result(
        self, 
        text: str, 
        target_language: SupportedLanguage, 
        source_language: str
    ) -> TranslationResult:
        """Create result for empty text"""
        return TranslationResult(
            original_text=text,
            translated_text=text,
            source_language=source_language,
            target_language=target_language,
            model_used=self.model,
            processing_time=0.0
        )
    
    async def translate_transcription(
        self, 
        transcription: TranscriptionResult, 
        target_language: SupportedLanguage,
        source_language: Optional[str] = None
    ) -> TranslationResult:
        """Translate transcription with metadata preservation"""
        try:
            start_time = time.time()
            
            # Use provided source language or auto-detect
            if not source_language:
                source_language = await self.detect_language(transcription.text)
            
            # Extract all segment texts for batch translation
            segment_texts = []
            segment_indices = []
            translated_segments = []
            
            if transcription.segments:
                for i, segment in enumerate(transcription.segments):
                    if segment.text.strip():
                        segment_texts.append(segment.text)
                        segment_indices.append(i)
                
                # Batch translate all segments at once
                if segment_texts:
                    logger.info(f"Starting batch translation of {len(segment_texts)} segments")
                    segment_translations = await self.translate_batch(
                        segment_texts, target_language, source_language
                    )
                    
                    # Map translations back to segments
                    translation_map = dict(zip(segment_indices, segment_translations))
                    
                    for i, segment in enumerate(transcription.segments):
                        if i in translation_map:
                            translation = translation_map[i]
                            translated_segment = TranslationSegment(
                                start_time=segment.start,
                                end_time=segment.end,
                                original_text=segment.text,
                                translated_text=translation.translated_text,
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
            
            async with self.semaphore:
                response = await self.client.chat.completions.create(
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