"""
Centralized settings management using pydantic
"""

from functools import lru_cache
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Configuration
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    
    # OpenAI API Configuration (for text processing)
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_base_url: str = Field("https://api.openai.com/v1", env="OPENAI_BASE_URL")
    openai_model: str = Field("gpt-4o-mini", env="OPENAI_MODEL")
    openai_temperature: float = Field(0.3, env="OPENAI_TEMPERATURE")
    openai_max_concurrent_requests: int = Field(10, env="OPENAI_MAX_CONCURRENT_REQUESTS")
    openai_max_tokens: int = Field(4000, env="OPENAI_MAX_TOKENS")
    
    # Audio Processing Configuration
    max_chunk_size_mb: int = Field(24, env="MAX_CHUNK_SIZE_MB")
    chunk_timeout_seconds: int = Field(120, env="CHUNK_TIMEOUT_SECONDS")
    audio_formats: List[str] = Field(["mp3", "m4a", "wav"], env="AUDIO_FORMATS")
    video_formats: List[str] = Field(["mp4", "avi", "mov", "wmv", "flv", "mkv", "webm"], env="VIDEO_FORMATS")
    audio_quality: str = Field("128k", env="AUDIO_QUALITY")
    
    # YouTube Download Configuration
    youtube_socket_timeout: int = Field(30, env="YOUTUBE_SOCKET_TIMEOUT")
    youtube_retries: int = Field(3, env="YOUTUBE_RETRIES")
    youtube_preferred_format: str = Field("m4a", env="YOUTUBE_PREFERRED_FORMAT")
    
    # Transcription Configuration
    whisper_model: str = Field("whisper-large-v3-turbo", env="WHISPER_MODEL")
    whisper_temperature: float = Field(0.0, env="WHISPER_TEMPERATURE")
    whisper_response_format: str = Field("verbose_json", env="WHISPER_RESPONSE_FORMAT")
    
    # Translation Configuration
    translation_model: str = Field("llama-3.3-70b-versatile", env="TRANSLATION_MODEL")
    translation_temperature: float = Field(0.3, env="TRANSLATION_TEMPERATURE")
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
    
    @field_validator("groq_api_key")
    @classmethod
    def validate_groq_api_key(cls, v):
        if not v or v.strip() == "":
            raise ValueError("GROQ_API_KEY is required")
        return v.strip()
    
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