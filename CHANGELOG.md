# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed
- **FasterWhisperProvider**: Removed unused FasterWhisperProvider implementation (use StableWhisperProvider instead)
  - Simplified codebase by removing redundant local model provider
  - StableWhisperProvider remains as the sole local model implementation

### Added

#### Local Whisper Model Support
- **Local Model Inference**: Added support for offline transcription using stable-whisper library
  - No API key required for local model usage
  - Support for 7 Whisper model sizes: tiny, base, small, medium, large, large-v2, large-v3
  - Automatic model download and caching on first use

- **Hardware Acceleration**:
  - CPU inference with optimized int8 quantization
  - CUDA GPU acceleration with float16/float32 precision
  - Apple Silicon (MPS) support for M1/M2 Macs
  - Auto-detection and fallback for unavailable devices

- **CLI Flags for Local Models**:
  - `--local-model`: Specify Whisper model size
  - `--local-device`: Choose compute device (cpu/cuda/mps)
  - `--local-compute-type`: Set precision (int8/int16/float16/float32)
  - `--local-beam-size`: Control beam search size (1-10)
  - `--local-temperature`: Adjust sampling temperature (0.0-1.0)
  - `--local-vad-filter`: Enable voice activity detection
  - `--local-max-workers`: Control concurrent processing (1-10)

- **Environment Variable Configuration**:
  - `SOGON_PROVIDER`: Set default transcription provider (stable-whisper/openai/groq)
  - `SOGON_LOCAL_MODEL_NAME`: Default local model
  - `SOGON_LOCAL_DEVICE`: Default compute device
  - `SOGON_LOCAL_COMPUTE_TYPE`: Default precision
  - `SOGON_LOCAL_BEAM_SIZE`: Default beam size
  - `SOGON_LOCAL_LANGUAGE`: Force language (skip auto-detection)
  - `SOGON_LOCAL_TEMPERATURE`: Default temperature
  - `SOGON_LOCAL_VAD_FILTER`: Enable VAD by default
  - `SOGON_LOCAL_MAX_WORKERS`: Default worker count
  - `SOGON_LOCAL_CACHE_MAX_SIZE_GB`: Model cache size limit
  - `SOGON_LOCAL_DOWNLOAD_ROOT`: Custom model storage path

- **Resource Management**:
  - Automatic disk space validation before model download
  - RAM/VRAM availability checks before model loading
  - Intelligent caching with size limits and LRU eviction
  - Concurrent job semaphore for memory management

- **Provider Architecture**:
  - Abstract `TranscriptionProvider` interface for extensibility
  - `StableWhisperProvider` implementation with async support
  - Device selector with capability detection
  - Resource monitor for system validation
  - Model manager with download progress tracking

### Changed

- **Configuration System**: Extended Settings with 10 new local model configuration fields
- **CLI Integration**: ServiceContainer now supports provider pattern with lazy loading
- **Transcription Service**: Updated to support both legacy API-based and new provider-based flows
- **Backward Compatibility**: Existing OpenAI and Groq workflows unchanged

### Technical Details

- **Provider Pattern**: Gradual migration strategy allowing coexistence of legacy and new providers
- **Lazy Loading**: Provider instantiation deferred until first use to avoid circular dependencies
- **Auto-Provider Switching**: Using `--local-model` flag automatically sets provider to "stable-whisper"
- **Priority Configuration**: CLI flags > Environment variables > Default values
- **Test Coverage**: 100% unit test coverage for all local model components
- **Integration Tests**: Comprehensive E2E tests for local transcription workflows

### Installation

```bash
# Install with local model support
pipx install sogon[local]

# Or for development
uv sync --extra local
```

### Usage Examples

```bash
# Basic local transcription
sogon run "video.mp4" --local-model base

# GPU acceleration
sogon run "video.mp4" --local-model base --local-device cuda

# High accuracy with larger model
sogon run "video.mp4" --local-model large-v3

# Environment variable configuration
export SOGON_PROVIDER=stable-whisper
export SOGON_LOCAL_MODEL_NAME=medium
sogon run "video.mp4"
```

## [Previous Releases]

<!-- Add previous release notes here when available -->
