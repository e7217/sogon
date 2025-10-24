"""Configuration test fixtures for local model testing."""

from pathlib import Path
from typing import Dict, Any


# Valid LocalModelConfiguration samples
VALID_CONFIG_CPU_TINY = {
    "model_name": "tiny",
    "device": "cpu",
    "compute_type": "int8",
    "beam_size": 5,
    "language": None,
    "temperature": 0.0,
    "vad_filter": False,
    "max_workers": 2,
    "cache_max_size_gb": 8.0,
    "download_root": Path.home() / ".cache" / "sogon" / "models",
}

VALID_CONFIG_CPU_BASE = {
    "model_name": "base",
    "device": "cpu",
    "compute_type": "int8",
    "beam_size": 5,
    "language": "en",
    "temperature": 0.0,
    "vad_filter": False,
    "max_workers": 2,
    "cache_max_size_gb": 8.0,
    "download_root": Path.home() / ".cache" / "sogon" / "models",
}

VALID_CONFIG_CUDA_MEDIUM = {
    "model_name": "medium",
    "device": "cuda",
    "compute_type": "float16",
    "beam_size": 5,
    "language": None,
    "temperature": 0.0,
    "vad_filter": True,
    "max_workers": 4,
    "cache_max_size_gb": 16.0,
    "download_root": Path.home() / ".cache" / "sogon" / "models",
}

VALID_CONFIG_CUDA_LARGE = {
    "model_name": "large-v3",
    "device": "cuda",
    "compute_type": "float16",
    "beam_size": 10,
    "language": "ko",
    "temperature": 0.2,
    "vad_filter": True,
    "max_workers": 2,
    "cache_max_size_gb": 16.0,
    "download_root": Path.home() / ".cache" / "sogon" / "models",
}

VALID_CONFIG_MPS_SMALL = {
    "model_name": "small",
    "device": "mps",
    "compute_type": "float16",
    "beam_size": 5,
    "language": "en",
    "temperature": 0.0,
    "vad_filter": False,
    "max_workers": 2,
    "cache_max_size_gb": 8.0,
    "download_root": Path.home() / ".cache" / "sogon" / "models",
}


# Invalid configuration examples for validation testing
INVALID_CONFIG_BAD_MODEL_NAME = {
    **VALID_CONFIG_CPU_BASE,
    "model_name": "invalid-model",  # Not in VALID_MODELS
}

INVALID_CONFIG_BAD_DEVICE = {
    **VALID_CONFIG_CPU_BASE,
    "device": "tpu",  # Not in VALID_DEVICES
}

INVALID_CONFIG_COMPUTE_TYPE_MISMATCH_CPU_FLOAT16 = {
    **VALID_CONFIG_CPU_BASE,
    "compute_type": "float16",  # float16 not valid for CPU
}

INVALID_CONFIG_COMPUTE_TYPE_MISMATCH_MPS_INT8 = {
    **VALID_CONFIG_MPS_SMALL,
    "compute_type": "int8",  # int8 not valid for MPS
}

INVALID_CONFIG_BEAM_SIZE_TOO_LOW = {
    **VALID_CONFIG_CPU_BASE,
    "beam_size": 0,  # Must be >= 1
}

INVALID_CONFIG_BEAM_SIZE_TOO_HIGH = {
    **VALID_CONFIG_CPU_BASE,
    "beam_size": 15,  # Must be <= 10
}

INVALID_CONFIG_TEMPERATURE_TOO_LOW = {
    **VALID_CONFIG_CPU_BASE,
    "temperature": -0.1,  # Must be >= 0.0
}

INVALID_CONFIG_TEMPERATURE_TOO_HIGH = {
    **VALID_CONFIG_CPU_BASE,
    "temperature": 1.5,  # Must be <= 1.0
}

INVALID_CONFIG_MAX_WORKERS_ZERO = {
    **VALID_CONFIG_CPU_BASE,
    "max_workers": 0,  # Must be >= 1
}

INVALID_CONFIG_CACHE_SIZE_ZERO = {
    **VALID_CONFIG_CPU_BASE,
    "cache_max_size_gb": 0.0,  # Must be > 0
}

INVALID_CONFIG_LANGUAGE_WRONG_LENGTH = {
    **VALID_CONFIG_CPU_BASE,
    "language": "eng",  # Must be 2 characters (ISO 639-1)
}


# All valid configs for parameterized testing
ALL_VALID_CONFIGS = [
    VALID_CONFIG_CPU_TINY,
    VALID_CONFIG_CPU_BASE,
    VALID_CONFIG_CUDA_MEDIUM,
    VALID_CONFIG_CUDA_LARGE,
    VALID_CONFIG_MPS_SMALL,
]

# All invalid configs with expected error messages
ALL_INVALID_CONFIGS = [
    (INVALID_CONFIG_BAD_MODEL_NAME, "Invalid model_name"),
    (INVALID_CONFIG_BAD_DEVICE, "Invalid device"),
    (INVALID_CONFIG_COMPUTE_TYPE_MISMATCH_CPU_FLOAT16, "Invalid compute_type"),
    (INVALID_CONFIG_COMPUTE_TYPE_MISMATCH_MPS_INT8, "Invalid compute_type"),
    (INVALID_CONFIG_BEAM_SIZE_TOO_LOW, "greater than or equal to 1"),
    (INVALID_CONFIG_BEAM_SIZE_TOO_HIGH, "less than or equal to 10"),
    (INVALID_CONFIG_TEMPERATURE_TOO_LOW, "greater than or equal to 0"),
    (INVALID_CONFIG_TEMPERATURE_TOO_HIGH, "less than or equal to 1"),
    (INVALID_CONFIG_MAX_WORKERS_ZERO, "greater than or equal to 1"),
    (INVALID_CONFIG_CACHE_SIZE_ZERO, "greater than 0"),
    (INVALID_CONFIG_LANGUAGE_WRONG_LENGTH, "2 characters"),
]


def create_env_vars_for_config(config: Dict[str, Any]) -> Dict[str, str]:
    """
    Convert config dict to environment variable dict.

    Args:
        config: Configuration dictionary

    Returns:
        Dict[str, str]: Environment variables
    """
    env_vars = {}

    if "model_name" in config:
        env_vars["SOGON_LOCAL_MODEL_NAME"] = config["model_name"]
    if "device" in config:
        env_vars["SOGON_LOCAL_DEVICE"] = config["device"]
    if "compute_type" in config:
        env_vars["SOGON_LOCAL_COMPUTE_TYPE"] = config["compute_type"]
    if "beam_size" in config:
        env_vars["SOGON_LOCAL_BEAM_SIZE"] = str(config["beam_size"])
    if "language" in config and config["language"]:
        env_vars["SOGON_LOCAL_LANGUAGE"] = config["language"]
    if "temperature" in config:
        env_vars["SOGON_LOCAL_TEMPERATURE"] = str(config["temperature"])
    if "vad_filter" in config:
        env_vars["SOGON_LOCAL_VAD_FILTER"] = str(config["vad_filter"]).lower()
    if "max_workers" in config:
        env_vars["SOGON_LOCAL_MAX_WORKERS"] = str(config["max_workers"])
    if "cache_max_size_gb" in config:
        env_vars["SOGON_LOCAL_CACHE_MAX_SIZE_GB"] = str(config["cache_max_size_gb"])
    if "download_root" in config:
        env_vars["SOGON_LOCAL_DOWNLOAD_ROOT"] = str(config["download_root"])

    return env_vars
