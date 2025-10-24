"""Audio file test fixtures and mock data generators."""

from pathlib import Path
from datetime import datetime
from sogon.models.audio import AudioFile, AudioChunk


def create_mock_audio_file(
    path: str = "/tmp/test_audio.mp3",
    duration_seconds: float = 225.0,  # 3m 45s
    size_bytes: int = 3_500_000,  # ~3.3 MB
    format: str = "mp3",
    sample_rate: int = 44100,
    channels: int = 2,
) -> AudioFile:
    """
    Create a mock AudioFile object for testing.

    Args:
        path: File path
        duration_seconds: Audio duration
        size_bytes: File size in bytes
        format: Audio format
        sample_rate: Sample rate in Hz
        channels: Number of audio channels

    Returns:
        AudioFile: Mock audio file object
    """
    return AudioFile(
        path=Path(path),
        duration_seconds=duration_seconds,
        size_bytes=size_bytes,
        format=format,
        sample_rate=sample_rate,
        channels=channels,
        bitrate="320k",
        created_at=datetime.now(),
    )


def create_small_audio_file() -> AudioFile:
    """Create a small audio file for quick tests (5 seconds)."""
    return create_mock_audio_file(
        path="/tmp/small_audio.mp3",
        duration_seconds=5.0,
        size_bytes=80_000,  # ~80 KB
    )


def create_medium_audio_file() -> AudioFile:
    """Create a medium audio file (3 minutes 45 seconds)."""
    return create_mock_audio_file(
        path="/tmp/medium_audio.mp3",
        duration_seconds=225.0,
        size_bytes=3_500_000,  # ~3.3 MB
    )


def create_large_audio_file() -> AudioFile:
    """Create a large audio file for testing (1 hour)."""
    return create_mock_audio_file(
        path="/tmp/large_audio.mp3",
        duration_seconds=3600.0,
        size_bytes=50_000_000,  # ~48 MB
    )


def create_audio_chunk(
    parent_file: AudioFile,
    chunk_number: int = 1,
    total_chunks: int = 1,
    start_time_seconds: float = 0.0,
    duration_seconds: float = 60.0,
) -> AudioChunk:
    """
    Create a mock AudioChunk object for testing.

    Args:
        parent_file: Parent AudioFile
        chunk_number: Chunk number (1-indexed)
        total_chunks: Total number of chunks
        start_time_seconds: Start time in seconds
        duration_seconds: Chunk duration

    Returns:
        AudioChunk: Mock audio chunk object
    """
    chunk_path = parent_file.path.parent / f"{parent_file.stem}_chunk{chunk_number}.mp3"
    return AudioChunk(
        path=chunk_path,
        parent_file=parent_file,
        chunk_number=chunk_number,
        total_chunks=total_chunks,
        start_time_seconds=start_time_seconds,
        duration_seconds=duration_seconds,
        size_bytes=int(parent_file.size_bytes / total_chunks),
        created_at=datetime.now(),
    )


# Pre-defined test audio files for common use cases
SAMPLE_AUDIO_5SEC = create_small_audio_file()
SAMPLE_AUDIO_3MIN = create_medium_audio_file()
SAMPLE_AUDIO_1HR = create_large_audio_file()


# Audio format helpers
SUPPORTED_AUDIO_FORMATS = ["mp3", "wav", "m4a", "flac", "ogg"]


def get_audio_duration_from_size(size_mb: float, bitrate_kbps: int = 320) -> float:
    """
    Estimate audio duration from file size and bitrate.

    Args:
        size_mb: File size in megabytes
        bitrate_kbps: Audio bitrate in kbps

    Returns:
        float: Estimated duration in seconds
    """
    size_kb = size_mb * 1024
    return (size_kb * 8) / bitrate_kbps


def is_audio_format_supported(filename: str) -> bool:
    """Check if audio format is supported based on filename."""
    ext = Path(filename).suffix.lstrip('.').lower()
    return ext in SUPPORTED_AUDIO_FORMATS
