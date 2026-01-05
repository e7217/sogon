"""
User configuration management with YAML persistence.

Provides CLI-based configuration management via `sogon config set/get` commands.
Configuration is stored in ~/.sogon/config.yaml
"""

from pathlib import Path
from typing import Any

import yaml


# Configuration keys that can be set via CLI
# Maps CLI key names to their Settings field names and descriptions
CONFIGURABLE_KEYS: dict[str, dict[str, Any]] = {
    # High Priority - User-facing behavior
    "output_base_dir": {
        "description": "Default output directory for results",
        "default": "./result",
        "type": str,
    },
    "default_subtitle_format": {
        "description": "Default subtitle output format",
        "default": "txt",
        "type": str,
        "choices": ["txt", "srt", "vtt", "json"],
    },
    "transcription_provider": {
        "description": "Transcription provider (groq, openai, stable-whisper)",
        "default": "groq",
        "type": str,
        "choices": ["groq", "openai", "stable-whisper"],
    },
    "default_translation_language": {
        "description": "Default target language for translation",
        "default": "ko",
        "type": str,
        "choices": ["ko", "en", "ja", "zh-cn", "zh-tw", "es", "fr", "de", "it", "pt", "ru", "ar", "hi", "th", "vi"],
    },
    "log_level": {
        "description": "Logging level",
        "default": "INFO",
        "type": str,
        "choices": ["DEBUG", "INFO", "WARNING", "ERROR"],
    },
    "keep_temp_files": {
        "description": "Keep temporary audio files after processing",
        "default": False,
        "type": bool,
    },
    "enable_translation": {
        "description": "Enable translation by default",
        "default": False,
        "type": bool,
    },
    "default_source_language": {
        "description": "Default source language (auto for auto-detect)",
        "default": "auto",
        "type": str,
        "choices": ["auto", "en", "ko", "ja", "zh", "es", "fr", "de", "it", "pt", "ru", "ar", "hi", "th", "vi"],
    },
    # Medium Priority - Local model configuration
    "local_model_name": {
        "description": "Local Whisper model name",
        "default": "base",
        "type": str,
        "choices": ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3", "large-v3-turbo"],
    },
    "local_device": {
        "description": "Compute device for local model",
        "default": "cuda",
        "type": str,
        "choices": ["cpu", "cuda", "mps"],
    },
    "local_compute_type": {
        "description": "Compute type for local model inference",
        "default": "float16",
        "type": str,
        "choices": ["int8", "int16", "float16", "float32"],
    },
    "local_beam_size": {
        "description": "Beam size for local model inference",
        "default": 5,
        "type": int,
        "min": 1,
        "max": 10,
    },
    "local_temperature": {
        "description": "Temperature for local model inference",
        "default": 0.0,
        "type": float,
        "min": 0.0,
        "max": 1.0,
    },
    "local_vad_filter": {
        "description": "Enable VAD filter for local model",
        "default": False,
        "type": bool,
    },
    # Performance tuning
    "max_workers": {
        "description": "Maximum concurrent workers",
        "default": 4,
        "type": int,
        "min": 1,
        "max": 16,
    },
    "max_chunk_size_mb": {
        "description": "Maximum audio chunk size in MB",
        "default": 24,
        "type": int,
        "min": 1,
        "max": 100,
    },
}


class UserConfigManager:
    """
    Manages user configuration stored in ~/.sogon/config.yaml

    Example usage:
        manager = UserConfigManager()
        manager.set("output_base_dir", "/custom/path")
        value = manager.get("output_base_dir")
        manager.reset("output_base_dir")
    """

    DEFAULT_CONFIG_DIR = Path.home() / ".sogon"
    DEFAULT_CONFIG_FILE = "config.yaml"

    def __init__(self, config_dir: Path | None = None):
        """
        Initialize the user config manager.

        Args:
            config_dir: Custom config directory. Defaults to ~/.sogon/
        """
        self.config_dir = config_dir or self.DEFAULT_CONFIG_DIR
        self.config_path = self.config_dir / self.DEFAULT_CONFIG_FILE
        self._config: dict[str, Any] = {}
        self._load()

    def _ensure_config_dir(self) -> None:
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                    self._config = loaded if loaded else {}
            except (yaml.YAMLError, OSError):
                self._config = {}
        else:
            self._config = {}

    def _save(self) -> None:
        """Save configuration to YAML file."""
        self._ensure_config_dir()
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self._config, f, default_flow_style=False, allow_unicode=True)

    def get(self, key: str) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key name

        Returns:
            The configured value, or None if not set

        Raises:
            KeyError: If key is not a valid configurable key
        """
        if key not in CONFIGURABLE_KEYS:
            raise KeyError(f"Unknown configuration key: {key}")
        return self._config.get(key)

    def get_all(self) -> dict[str, Any]:
        """
        Get all user-configured values.

        Returns:
            Dictionary of all set configuration values
        """
        return self._config.copy()

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key name
            value: Value to set

        Raises:
            KeyError: If key is not a valid configurable key
            ValueError: If value is invalid for the key
        """
        if key not in CONFIGURABLE_KEYS:
            raise KeyError(f"Unknown configuration key: {key}")

        validated_value = self._validate_value(key, value)
        self._config[key] = validated_value
        self._save()

    def reset(self, key: str | None = None) -> None:
        """
        Reset configuration to default.

        Args:
            key: Specific key to reset. If None, resets all configuration.

        Raises:
            KeyError: If key is not a valid configurable key
        """
        if key is None:
            self._config = {}
            self._save()
        else:
            if key not in CONFIGURABLE_KEYS:
                raise KeyError(f"Unknown configuration key: {key}")
            if key in self._config:
                del self._config[key]
                self._save()

    def _validate_value(self, key: str, value: Any) -> Any:
        """
        Validate and convert a value for a given key.

        Args:
            key: Configuration key name
            value: Value to validate

        Returns:
            Validated and type-converted value

        Raises:
            ValueError: If value is invalid
        """
        key_info = CONFIGURABLE_KEYS[key]
        expected_type = key_info["type"]

        # Type conversion
        try:
            if expected_type == bool:
                if isinstance(value, str):
                    if value.lower() in ("true", "1", "yes", "on"):
                        value = True
                    elif value.lower() in ("false", "0", "no", "off"):
                        value = False
                    else:
                        raise ValueError(f"Invalid boolean value: {value}")
                else:
                    value = bool(value)
            elif expected_type == int:
                value = int(value)
            elif expected_type == float:
                value = float(value)
            elif expected_type == str:
                value = str(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert '{value}' to {expected_type.__name__}: {e}") from e

        # Choices validation
        if "choices" in key_info:
            # Case-insensitive for strings
            if expected_type == str:
                value_lower = value.lower()
                choices_lower = [c.lower() for c in key_info["choices"]]
                if value_lower not in choices_lower:
                    raise ValueError(
                        f"Invalid value '{value}' for {key}. "
                        f"Must be one of: {', '.join(key_info['choices'])}"
                    )
                # Return the original case from choices
                for choice in key_info["choices"]:
                    if choice.lower() == value_lower:
                        value = choice
                        break
            elif value not in key_info["choices"]:
                raise ValueError(
                    f"Invalid value '{value}' for {key}. "
                    f"Must be one of: {', '.join(map(str, key_info['choices']))}"
                )

        # Range validation for numeric types
        if expected_type in (int, float):
            if "min" in key_info and value < key_info["min"]:
                raise ValueError(f"Value {value} for {key} must be >= {key_info['min']}")
            if "max" in key_info and value > key_info["max"]:
                raise ValueError(f"Value {value} for {key} must be <= {key_info['max']}")

        return value

    @staticmethod
    def list_keys() -> dict[str, dict[str, Any]]:
        """
        List all configurable keys with their metadata.

        Returns:
            Dictionary of key names to their metadata
        """
        return CONFIGURABLE_KEYS.copy()

    def get_effective_value(self, key: str) -> Any:
        """
        Get the effective value for a key (user config or default).

        Args:
            key: Configuration key name

        Returns:
            User-configured value if set, otherwise the default

        Raises:
            KeyError: If key is not a valid configurable key
        """
        if key not in CONFIGURABLE_KEYS:
            raise KeyError(f"Unknown configuration key: {key}")

        user_value = self._config.get(key)
        if user_value is not None:
            return user_value
        return CONFIGURABLE_KEYS[key]["default"]


# Singleton instance for easy access
_user_config_manager: UserConfigManager | None = None


def get_user_config_manager() -> UserConfigManager:
    """
    Get the singleton UserConfigManager instance.

    Returns:
        UserConfigManager instance
    """
    global _user_config_manager
    if _user_config_manager is None:
        _user_config_manager = UserConfigManager()
    return _user_config_manager


def reload_user_config() -> UserConfigManager:
    """
    Reload user configuration (clear cache and create new instance).

    Returns:
        New UserConfigManager instance
    """
    global _user_config_manager
    _user_config_manager = UserConfigManager()
    return _user_config_manager
