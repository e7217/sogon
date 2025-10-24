# Research: Local Whisper Model Support

**Date**: 2025-10-17
**Feature**: Add local Whisper model inference capability

## Research Questions & Decisions

### 1. Local Inference Library Selection

**Decision**: faster-whisper (CTranslate2-based)

**Rationale**:
- **Performance**: 4x faster than openai-whisper with same accuracy
- **Memory Efficiency**: Lower VRAM usage through CTranslate2 optimizations
- **Hardware Support**: CPU, CUDA (NVIDIA), and planned MPS (Apple Silicon) support
- **Mature**: Production-ready, actively maintained by Systran
- **Compatible**: Drop-in replacement for Whisper API patterns

**Alternatives Considered**:
- **openai-whisper** (official): Slower, higher memory usage, but reference implementation
- **whisper.cpp**: Fastest for CPU, but C++ integration complexity, limited Python bindings
- **transformers (Hugging Face)**: More flexible but slower, higher memory overhead
- **whisperX**: Better alignment features but overkill for basic transcription

**Implementation Path**:
```python
from faster_whisper import WhisperModel

model = WhisperModel(
    model_size_or_path="base",
    device="cuda",  # or "cpu"
    compute_type="float16"
)
segments, info = model.transcribe(audio_file, beam_size=5)
```

---

### 2. Model Distribution & Download Strategy

**Decision**: Hugging Face Hub with automatic download (per FR-002)

**Rationale**:
- **Official Repository**: Systran hosts faster-whisper models on HF
- **Reliable CDN**: HF's infrastructure ensures global availability
- **Version Control**: Models tagged with versions (large-v2, large-v3)
- **Caching Built-in**: HF hub client automatically caches to `~/.cache/huggingface/`
- **Progress Tracking**: Native progress bars for downloads

**Alternatives Considered**:
- **Bundle with package**: Too large (1-3GB per model), inflates package size
- **Manual download**: Poor UX, violates FR-002 auto-download requirement
- **OpenAI CDN**: Only serves API models, not local inference files

**Implementation Path**:
```python
from huggingface_hub import snapshot_download

model_path = snapshot_download(
    repo_id="Systran/faster-whisper-base",
    cache_dir="~/.cache/sogon/models",
    allow_patterns=["*.bin", "config.json"]
)
```

---

### 3. GPU Acceleration Libraries

**Decision**: torch + CUDA for Linux (initial), MPS for macOS (phase 2)

**Rationale**:
- **CUDA 11.8+**: Industry standard for NVIDIA GPU acceleration (NFR-005)
- **PyTorch**: faster-whisper requires torch for GPU operations
- **CTranslate2**: Automatically uses CUDA when available through torch
- **MPS Support**: PyTorch 2.0+ supports Apple Silicon via MPS backend (NFR-006)

**Alternatives Considered**:
- **TensorRT**: Faster but complex setup, overkill for Whisper
- **ONNX Runtime**: Good cross-platform but faster-whisper doesn't export ONNX
- **ROCm (AMD)**: Limited faster-whisper support, not prioritized

**Implementation Path**:
```python
import torch

def get_device():
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"  # macOS phase
    return "cpu"
```

---

### 4. Disk Space Management

**Decision**: Check before download + post-download verification (per FR-005)

**Rationale**:
- **shutil.disk_usage()**: Native Python, cross-platform
- **Safety Buffer**: Require 10% extra space beyond model size
- **Model Sizes**: tiny (75MB), base (142MB), small (466MB), medium (1.5GB), large (2.9GB)

**Implementation Path**:
```python
import shutil
from pathlib import Path

def check_disk_space(model_size: int, cache_dir: Path) -> bool:
    stat = shutil.disk_usage(cache_dir)
    required = model_size * 1.1  # 10% buffer
    return stat.free >= required
```

---

### 5. Memory Monitoring & Resource Management

**Decision**: psutil for memory tracking + graceful termination (per FR-021)

**Rationale**:
- **psutil**: Cross-platform memory monitoring
- **Thresholds**: Alert at 80% RAM, terminate at 90% RAM
- **VRAM Monitoring**: torch.cuda.memory_allocated() for GPU
- **LRU Cache**: functools.lru_cache decorator for model management (per FR-024)

**Implementation Path**:
```python
import psutil
import torch

def check_memory_available(min_gb: float = 2.0) -> bool:
    mem = psutil.virtual_memory()
    available_gb = mem.available / (1024**3)
    return available_gb >= min_gb

def check_vram_available(min_gb: float = 2.0) -> bool:
    if not torch.cuda.is_available():
        return True
    free_vram = torch.cuda.mem_get_info()[0] / (1024**3)
    return free_vram >= min_gb
```

---

### 6. Provider Pattern Architecture

**Decision**: Abstract TranscriptionProvider + Concrete Implementations

**Rationale**:
- **Existing Pattern**: sogon already uses provider pattern for correction/translation (NFR-007)
- **Polymorphism**: Clean interface for API vs local providers
- **Testability**: Easy to mock providers for unit tests
- **Extensibility**: Add new providers (Groq local, WhisperX) without modifying core

**Class Hierarchy**:
```
TranscriptionProvider (ABC)
├── OpenAIProvider (existing, refactored)
├── GroqProvider (existing, refactored)
└── FasterWhisperProvider (new)
    ├── ModelManager (composition)
    └── DeviceSelector (composition)
```

---

### 7. Configuration Schema

**Decision**: Pydantic models with environment variable support (existing pattern)

**Rationale**:
- **Consistency**: sogon already uses Pydantic Settings
- **Validation**: Type-safe configuration with runtime validation
- **Environment Variables**: Automatic parsing from SOGON_* prefix
- **CLI Integration**: Typer automatically maps Pydantic models to CLI args

**Schema**:
```python
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class LocalModelConfig(BaseModel):
    model_name: str = Field(default="base", description="Whisper model size")
    device: str = Field(default="cpu", description="Compute device")
    compute_type: str = Field(default="int8", description="Precision")
    beam_size: int = Field(default=5, description="Beam search size")
    max_workers: int = Field(default=2, description="Concurrent jobs")
    cache_max_size_gb: float = Field(default=8.0, description="Max cache size")

class TranscriptionSettings(BaseSettings):
    provider: str = Field(default="openai", description="Provider type")
    local: LocalModelConfig = Field(default_factory=LocalModelConfig)

    class Config:
        env_prefix = "SOGON_"
```

---

### 8. Concurrent Job Management

**Decision**: asyncio.Semaphore with default limit of 2 (per FR-022, FR-023)

**Rationale**:
- **Thread-Safe**: asyncio primitives handle concurrency correctly
- **Resource Control**: Prevents memory exhaustion from parallel jobs
- **Configurable**: User can override via SOGON_MAX_WORKERS
- **Existing Pattern**: sogon's WorkflowService already async

**Implementation Path**:
```python
import asyncio

class LocalTranscriptionProvider:
    def __init__(self, max_workers: int = 2):
        self._semaphore = asyncio.Semaphore(max_workers)

    async def transcribe(self, audio_file: Path):
        async with self._semaphore:
            # Only max_workers transcriptions run concurrently
            result = await self._transcribe_impl(audio_file)
            return result
```

---

### 9. Model Caching Strategy

**Decision**: LRU eviction with size-based limits (per FR-024)

**Rationale**:
- **Memory Efficiency**: Prevents RAM exhaustion
- **Performance**: Reuse loaded models across jobs
- **Simple**: Python's @lru_cache for in-process cache
- **Configurable**: SOGON_CACHE_MAX_SIZE_GB environment variable

**Implementation Path**:
```python
from functools import lru_cache
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelKey:
    model_name: str
    device: str
    compute_type: str

@lru_cache(maxsize=3)  # Cache up to 3 models
def load_model(key: ModelKey) -> WhisperModel:
    return WhisperModel(
        model_size_or_path=key.model_name,
        device=key.device,
        compute_type=key.compute_type
    )
```

---

### 10. Testing Strategy

**Decision**: Contract tests → Unit tests → Integration tests (per user directive)

**Rationale**:
- **Contract Tests**: Define provider interface behavior
- **Unit Tests**: Test each component in isolation with mocks
- **Integration Tests**: Verify end-to-end transcription with real models (small size)
- **TDD**: Tests written first, implementation second

**Test Structure**:
```
tests/
├── contract/
│   └── test_transcription_provider_contract.py  # Interface tests
├── unit/
│   ├── test_faster_whisper_provider.py          # Provider logic
│   ├── test_model_manager.py                    # Model lifecycle
│   └── test_device_selector.py                  # Device detection
└── integration/
    └── test_local_transcription_e2e.py          # Full workflow
```

---

## Dependency Matrix

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| Local Inference | faster-whisper | >=1.0.0 | Whisper model execution |
| GPU Support | torch | >=2.0.0 | CUDA/MPS acceleration |
| Model Downloads | huggingface-hub | >=0.20.0 | Model repository access |
| Memory Monitoring | psutil | >=5.9.0 | RAM/CPU tracking |
| Configuration | pydantic | >=2.9.0 | Type-safe settings |
| Testing | pytest | >=7.0.0 | Test framework |
| Mocking | pytest-mock | >=3.10.0 | Test doubles |

**Optional Dependencies** (per FR-030, FR-031):
```toml
[project.optional-dependencies]
local = [
    "faster-whisper>=1.0.0",
    "torch>=2.0.0",
    "huggingface-hub>=0.20.0",
    "psutil>=5.9.0",
]
```

---

## Performance Benchmarks (Research)

Based on faster-whisper documentation and community benchmarks:

| Model | Size | CPU (8-core) | GPU (RTX 3060) | Memory (CPU) | VRAM (GPU) |
|-------|------|--------------|----------------|--------------|------------|
| tiny | 75MB | 8x realtime | 50x realtime | 1GB | 1GB |
| base | 142MB | 5x realtime | 40x realtime | 1.5GB | 1.5GB |
| small | 466MB | 3x realtime | 25x realtime | 2GB | 2GB |
| medium | 1.5GB | 2x realtime | 15x realtime | 4GB | 4GB |
| large-v2 | 2.9GB | 1x realtime | 10x realtime | 8GB | 8GB |

**Meets Requirements**: ✅ GPU ≥10x realtime, ✅ CPU ≥2x realtime (for base/small models)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GPU driver incompatibility | Medium | High | Fallback to CPU, clear error messages (FR-009) |
| Model download failure | Low | High | Retry logic, cache verification, offline mode docs |
| Memory exhaustion | Medium | Medium | Proactive monitoring (FR-021), clear limits |
| CUDA version mismatch | Medium | Medium | Document CUDA 11.8+ requirement (NFR-005, FR-032) |
| Model cache corruption | Low | Low | Hash verification, re-download on validation failure |

---

## Migration Path

**Phase 1 (Initial)**: Linux + CUDA support
**Phase 2 (Future)**: macOS + MPS support
**Phase 3 (Future)**: Windows support

**Backward Compatibility**: All existing API-based configurations continue working unchanged (FR-017).

---

## Research Complete

All technical unknowns resolved. Ready for Phase 1 design.
