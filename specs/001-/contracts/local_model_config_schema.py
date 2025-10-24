"""
LocalModelConfiguration Schema Contract

Defines the data schema for local Whisper model configuration.
Used by FasterWhisperProvider and validated by Pydantic.
"""

from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


# Valid model names from Whisper
VALID_MODELS = {
    "tiny",
    "base",
    "small",
    "medium",
    "large",
    "large-v2",
    "large-v3",
}

# Valid compute devices
VALID_DEVICES = {"cpu", "cuda", "mps"}

# Valid compute types per device
DEVICE_COMPUTE_TYPES = {
    "cpu": {"int8", "int16"},
    "cuda": {"int8", "float16", "float32"},
    "mps": {"float16", "float32"},
}


class LocalModelConfiguration(BaseModel):
    """
    Configuration for local Whisper model inference.

    Attributes validated per FR-004, FR-006, FR-008, FR-010, FR-020, FR-023.
    """

    model_config = ConfigDict(
        frozen=False,  # Allow mutation for testing
        extra="forbid",  # Strict schema - no extra fields
        str_strip_whitespace=True,
    )

    # Model Selection (FR-004, FR-010)
    model_name: str = Field(
        default="base",
        description="Whisper model size to use",
        examples=["tiny", "base", "small", "medium", "large-v3"],
    )

    # Device Configuration (FR-006, FR-010)
    device: Literal["cpu", "cuda", "mps"] = Field(
        default="cpu",
        description="Compute device for inference",
    )

    # Precision Settings (FR-008)
    compute_type: str = Field(
        default="int8",
        description="Numerical precision for inference",
        examples=["int8", "float16", "float32"],
    )

    # Inference Parameters
    beam_size: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Beam search width (higher = more accurate but slower)",
    )

    language: str | None = Field(
        default=None,
        description="Force specific language (ISO 639-1 code) or None for auto-detect",
        examples=["en", "es", "fr", "de", "ja", "ko", None],
    )

    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Sampling temperature (0.0 = greedy, higher = more random)",
    )

    vad_filter: bool = Field(
        default=False,
        description="Enable Voice Activity Detection filter (reduces hallucinations)",
    )

    # Concurrency & Resource Management (FR-022, FR-023)
    max_workers: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Maximum concurrent transcription jobs",
    )

    # Cache Configuration (FR-024)
    cache_max_size_gb: float = Field(
        default=8.0,
        gt=0.0,
        description="Maximum model cache size in gigabytes",
    )

    # Storage Configuration (FR-002)
    download_root: Path = Field(
        default_factory=lambda: Path.home() / ".cache" / "sogon" / "models",
        description="Directory for downloaded model files",
    )

    # Validators

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Ensure model name is valid (FR-004)"""
        if v not in VALID_MODELS:
            raise ValueError(
                f"Invalid model_name '{v}'. "
                f"Must be one of: {', '.join(sorted(VALID_MODELS))}"
            )
        return v

    @field_validator("device")
    @classmethod
    def validate_device(cls, v: str) -> str:
        """Ensure device is valid (FR-006)"""
        if v not in VALID_DEVICES:
            raise ValueError(
                f"Invalid device '{v}'. Must be one of: {', '.join(VALID_DEVICES)}"
            )
        return v

    @field_validator("compute_type")
    @classmethod
    def validate_compute_type(cls, v: str, info) -> str:
        """Ensure compute_type matches device capabilities (FR-008)"""
        device = info.data.get("device", "cpu")
        valid_types = DEVICE_COMPUTE_TYPES.get(device, set())

        if v not in valid_types:
            raise ValueError(
                f"Invalid compute_type '{v}' for device '{device}'. "
                f"Valid options: {', '.join(valid_types)}"
            )
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        """Validate ISO 639-1 language code if provided"""
        if v is None:
            return v

        # Common Whisper-supported languages
        SUPPORTED_LANGUAGES = {
            "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
            "ar", "hi", "tr", "pl", "nl", "sv", "da", "fi", "no", "cs",
        }

        if len(v) != 2:
            raise ValueError(f"Language code must be 2 characters (ISO 639-1), got: {v}")

        if v not in SUPPORTED_LANGUAGES:
            # Warning but allow - Whisper supports 90+ languages
            pass

        return v.lower()

    @field_validator("download_root")
    @classmethod
    def validate_download_root(cls, v: Path) -> Path:
        """Ensure download root is absolute path"""
        return v.expanduser().resolve()

    def get_model_size_estimate_gb(self) -> float:
        """
        Estimate model size for disk space checking (FR-005).

        Returns:
            float: Estimated model size in GB
        """
        MODEL_SIZES_GB = {
            "tiny": 0.075,
            "base": 0.142,
            "small": 0.466,
            "medium": 1.5,
            "large": 2.9,
            "large-v2": 2.9,
            "large-v3": 2.9,
        }
        return MODEL_SIZES_GB.get(self.model_name, 1.0)

    def get_min_ram_gb(self) -> float:
        """
        Get minimum RAM requirement for this configuration (FR-021).

        Returns:
            float: Minimum RAM in GB
        """
        MODEL_RAM_GB = {
            "tiny": 1.0,
            "base": 1.5,
            "small": 2.0,
            "medium": 4.0,
            "large": 8.0,
            "large-v2": 8.0,
            "large-v3": 8.0,
        }
        return MODEL_RAM_GB.get(self.model_name, 2.0)

    def get_min_vram_gb(self) -> float:
        """
        Get minimum VRAM requirement for GPU inference (FR-021).

        Returns:
            float: Minimum VRAM in GB (0 if CPU)
        """
        if self.device == "cpu":
            return 0.0

        MODEL_VRAM_GB = {
            "tiny": 1.0,
            "base": 1.5,
            "small": 2.0,
            "medium": 4.0,
            "large": 8.0,
            "large-v2": 8.0,
            "large-v3": 8.0,
        }
        return MODEL_VRAM_GB.get(self.model_name, 2.0)


# Contract Tests
"""
Contract test requirements:

1. test_valid_configs():
   - Create configs with all valid combinations
   - Assert no validation errors

2. test_invalid_model_name():
   - Try invalid model_name
   - Assert ValueError with clear message

3. test_invalid_device():
   - Try invalid device
   - Assert ValueError

4. test_compute_type_device_mismatch():
   - Try float16 on CPU
   - Try int8 on MPS
   - Assert ValueError with explanation

5. test_resource_estimates():
   - Verify get_model_size_estimate_gb() accuracy
   - Verify get_min_ram_gb() meets requirements
   - Verify get_min_vram_gb() for GPU vs CPU

6. test_environment_variable_parsing():
   - Set SOGON_LOCAL_MODEL_NAME=small
   - Assert config.model_name == "small"

7. test_cli_flag_parsing():
   - Parse --local-model large --device cuda
   - Assert correct config created
"""
