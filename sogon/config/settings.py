"""
Centralized settings management using pydantic
"""

from functools import lru_cache
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Legacy API Configuration (for backward compatibility)
    groq_api_key: str = Field(None, env="GROQ_API_KEY")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_base_url: str = Field("https://api.openai.com/v1", env="OPENAI_BASE_URL")
    openai_model: str = Field("gpt-4o-mini", env="OPENAI_MODEL")
    openai_temperature: float = Field(0.3, env="OPENAI_TEMPERATURE")
    openai_max_concurrent_requests: int = Field(10, env="OPENAI_MAX_CONCURRENT_REQUESTS")
    openai_max_tokens: int = Field(4000, env="OPENAI_MAX_TOKENS")

    # Transcription Service Configuration
    transcription_provider: str = Field("groq", env="TRANSCRIPTION_PROVIDER")
    transcription_api_key: str = Field(None, env="TRANSCRIPTION_API_KEY")
    transcription_base_url: str = Field("https://api.groq.com/openai/v1", env="TRANSCRIPTION_BASE_URL")
    transcription_model: str = Field("whisper-large-v3-turbo", env="TRANSCRIPTION_MODEL")
    transcription_temperature: float = Field(0.0, env="TRANSCRIPTION_TEMPERATURE")
    transcription_response_format: str = Field("verbose_json", env="TRANSCRIPTION_RESPONSE_FORMAT")

    # Translation Service Configuration
    translation_provider: str = Field("openai", env="TRANSLATION_PROVIDER")
    translation_api_key: str = Field(None, env="TRANSLATION_API_KEY")
    translation_base_url: str = Field("https://api.openai.com/v1", env="TRANSLATION_BASE_URL")
    translation_model: str = Field("gpt-4o-mini", env="TRANSLATION_MODEL")
    translation_temperature: float = Field(0.3, env="TRANSLATION_TEMPERATURE")
    translation_max_tokens: int = Field(4000, env="TRANSLATION_MAX_TOKENS")

    # Correction Service Configuration
    correction_provider: str = Field("openai", env="CORRECTION_PROVIDER")
    correction_api_key: str = Field(None, env="CORRECTION_API_KEY")
    correction_base_url: str = Field("https://api.openai.com/v1", env="CORRECTION_BASE_URL")
    correction_model: str = Field("gpt-4o-mini", env="CORRECTION_MODEL")
    correction_temperature: float = Field(0.1, env="CORRECTION_TEMPERATURE")
    correction_max_tokens: int = Field(4000, env="CORRECTION_MAX_TOKENS")
    enable_correction_by_default: bool = Field(False, env="ENABLE_CORRECTION_BY_DEFAULT")
    
    # Audio Processing Configuration
    max_chunk_size_mb: int = Field(24, env="MAX_CHUNK_SIZE_MB")
    chunk_timeout_seconds: int = Field(120, env="CHUNK_TIMEOUT_SECONDS")
    audio_formats: List[str] = Field(["mp3", "m4a", "wav"], env="AUDIO_FORMATS")
    video_formats: List[str] = Field(["mp4", "avi", "mov", "wmv", "flv", "mkv", "webm"], env="VIDEO_FORMATS")
    audio_quality: str = Field("128k", env="AUDIO_QUALITY")
    audio_sample_rate: int = Field(16000, env="AUDIO_SAMPLE_RATE")
    audio_channels: int = Field(1, env="AUDIO_CHANNELS")  # 1=mono, 2=stereo
    
    # YouTube Download Configuration
    youtube_socket_timeout: int = Field(30, env="YOUTUBE_SOCKET_TIMEOUT")
    youtube_retries: int = Field(3, env="YOUTUBE_RETRIES")
    youtube_preferred_format: str = Field("m4a", env="YOUTUBE_PREFERRED_FORMAT")
    
    # General Translation Configuration
    enable_translation_by_default: bool = Field(False, env="ENABLE_TRANSLATION_BY_DEFAULT")
    default_translation_language: str = Field("ko", env="DEFAULT_TRANSLATION_LANGUAGE")
    
    # File Management Configuration
    keep_temp_files: bool = Field(False, env="KEEP_TEMP_FILES")
    output_base_dir: str = Field("./result", env="OUTPUT_BASE_DIR")
    
    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("sogon.log", env="LOG_FILE")
    log_max_bytes: int = Field(10*1024*1024, env="LOG_MAX_BYTES")  # 10MB
    log_backup_count: int = Field(5, env="LOG_BACKUP_COUNT")
    
    # Performance Configuration
    max_workers: int = Field(4, env="MAX_WORKERS")
    
    # Processing Timeout Configuration
    max_processing_timeout_seconds: int = Field(1800, env="MAX_PROCESSING_TIMEOUT_SECONDS")  # 30 minutes
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_api_key(cls, v):
        if not v or v.strip() == "":
            raise ValueError("OPENAI_API_KEY is required")
        return v.strip()
    
    @field_validator("max_chunk_size_mb")
    @classmethod
    def validate_max_chunk_size(cls, v):
        if v <= 0 or v > 100:
            raise ValueError("max_chunk_size_mb must be between 1 and 100")
        return v
    
    @field_validator("audio_formats")
    @classmethod
    def validate_audio_formats(cls, v):
        if isinstance(v, str):
            # Handle comma-separated string from env var
            v = [fmt.strip() for fmt in v.split(",")]
        supported_formats = ["mp3", "m4a", "wav", "flac", "aac"]
        for fmt in v:
            if fmt not in supported_formats:
                raise ValueError(f"Unsupported audio format: {fmt}")
        return v
    
    @field_validator("video_formats")
    @classmethod
    def validate_video_formats(cls, v):
        if isinstance(v, str):
            # Handle comma-separated string from env var
            v = [fmt.strip() for fmt in v.split(",")]
        supported_formats = ["mp4", "avi", "mov", "wmv", "flv", "mkv", "webm"]
        for fmt in v:
            if fmt not in supported_formats:
                raise ValueError(f"Unsupported video format: {fmt}")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of: {valid_levels}")
        return v.upper()
    
    @field_validator("default_translation_language")
    @classmethod
    def validate_translation_language(cls, v):
        valid_languages = ["ko", "en", "ja", "zh-cn", "zh-tw", "es", "fr", "de", "it", "pt", "ru", "ar", "hi", "th", "vi"]
        if v not in valid_languages:
            raise ValueError(f"default_translation_language must be one of: {valid_languages}")
        return v

    @field_validator("audio_sample_rate")
    @classmethod
    def validate_audio_sample_rate(cls, v):
        valid_rates = [8000, 16000, 22050, 44100, 48000]
        if v not in valid_rates:
            raise ValueError(f"audio_sample_rate must be one of: {valid_rates}")
        return v

    @field_validator("audio_channels")
    @classmethod
    def validate_audio_channels(cls, v):
        if v not in [1, 2]:
            raise ValueError("audio_channels must be 1 (mono) or 2 (stereo)")
        return v

    @field_validator("transcription_provider")
    @classmethod
    def validate_transcription_provider(cls, v):
        valid_providers = ["groq", "openai"]
        if v not in valid_providers:
            raise ValueError(f"transcription_provider must be one of: {valid_providers}")
        return v

    @field_validator("translation_provider")
    @classmethod
    def validate_translation_provider(cls, v):
        valid_providers = ["openai", "azure", "anthropic"]
        if v not in valid_providers:
            raise ValueError(f"translation_provider must be one of: {valid_providers}")
        return v

    @field_validator("correction_provider")
    @classmethod
    def validate_correction_provider(cls, v):
        valid_providers = ["openai", "azure", "anthropic"]
        if v not in valid_providers:
            raise ValueError(f"correction_provider must be one of: {valid_providers}")
        return v

    # Compatibility properties for backward compatibility
    @property
    def effective_transcription_api_key(self) -> str:
        """Get effective transcription API key with fallback"""
        if self.transcription_api_key:
            return self.transcription_api_key
        elif self.transcription_provider == "groq":
            return self.groq_api_key
        else:
            return self.openai_api_key

    @property
    def effective_translation_api_key(self) -> str:
        """Get effective translation API key with fallback"""
        return self.translation_api_key or self.openai_api_key

    @property
    def effective_correction_api_key(self) -> str:
        """Get effective correction API key with fallback"""
        return self.correction_api_key or self.openai_api_key


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    
    Returns:
        Settings: Configured settings instance
    """
    return Settings()


def reload_settings() -> Settings:
    """
    Reload settings (clear cache and create new instance)
    
    Returns:
        Settings: New settings instance
    """
    get_settings.cache_clear()
    return get_settings()