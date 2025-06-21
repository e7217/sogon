"""
Configuration validation utilities
"""

import os
import logging
from pathlib import Path
from typing import List, Tuple

from .settings import Settings

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Configuration validation error"""
    pass


def validate_environment() -> Tuple[bool, List[str]]:
    """
    Validate environment configuration
    
    Returns:
        Tuple[bool, List[str]]: (is_valid, error_messages)
    """
    errors = []
    
    try:
        settings = Settings()
    except Exception as e:
        errors.append(f"Failed to load settings: {e}")
        return False, errors
    
    # Validate required environment variables
    if not os.getenv("GROQ_API_KEY"):
        errors.append("GROQ_API_KEY environment variable is required")
    
    # Validate output directory
    try:
        output_dir = Path(settings.output_base_dir)
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        if not output_dir.is_dir():
            errors.append(f"Output directory is not a directory: {settings.output_base_dir}")
        if not os.access(output_dir, os.W_OK):
            errors.append(f"Output directory is not writable: {settings.output_base_dir}")
    except Exception as e:
        errors.append(f"Invalid output directory: {e}")
    
    # Validate log file directory
    try:
        log_file = Path(settings.log_file)
        log_dir = log_file.parent
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
        if not os.access(log_dir, os.W_OK):
            errors.append(f"Log directory is not writable: {log_dir}")
    except Exception as e:
        errors.append(f"Invalid log file path: {e}")
    
    # Validate numeric ranges
    if settings.max_workers <= 0:
        errors.append("max_workers must be greater than 0")
    
    if settings.chunk_timeout_seconds <= 0:
        errors.append("chunk_timeout_seconds must be greater than 0")
    
    return len(errors) == 0, errors


def check_dependencies() -> Tuple[bool, List[str]]:
    """
    Check if required external dependencies are available
    
    Returns:
        Tuple[bool, List[str]]: (is_valid, error_messages)
    """
    errors = []
    
    # Check ffmpeg
    try:
        import subprocess
        result = subprocess.run(["ffmpeg", "-version"], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode != 0:
            errors.append("ffmpeg is not working properly")
    except FileNotFoundError:
        errors.append("ffmpeg is not installed or not in PATH")
    except subprocess.TimeoutExpired:
        errors.append("ffmpeg command timed out")
    except Exception as e:
        errors.append(f"Error checking ffmpeg: {e}")
    
    # Check ffprobe
    try:
        import subprocess
        result = subprocess.run(["ffprobe", "-version"], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode != 0:
            errors.append("ffprobe is not working properly")
    except FileNotFoundError:
        errors.append("ffprobe is not installed or not in PATH")
    except subprocess.TimeoutExpired:
        errors.append("ffprobe command timed out")
    except Exception as e:
        errors.append(f"Error checking ffprobe: {e}")
    
    return len(errors) == 0, errors


def validate_configuration() -> None:
    """
    Validate complete configuration and raise error if invalid
    
    Raises:
        ConfigurationError: If configuration is invalid
    """
    all_errors = []
    
    # Validate environment
    env_valid, env_errors = validate_environment()
    if not env_valid:
        all_errors.extend(env_errors)
    
    # Check dependencies
    deps_valid, deps_errors = check_dependencies()
    if not deps_valid:
        all_errors.extend(deps_errors)
    
    if all_errors:
        error_message = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in all_errors)
        logger.error(error_message)
        raise ConfigurationError(error_message)
    
    logger.info("Configuration validation passed")


if __name__ == "__main__":
    # Allow running validation directly
    try:
        validate_configuration()
        print("Configuration is valid")
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
        exit(1)