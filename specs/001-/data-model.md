# Data Model: Local Whisper Model Support

**Feature**: Local Whisper model inference capability
**Date**: 2025-10-17

## Entity Definitions

### 1. TranscriptionProvider (Abstract Interface)

**Purpose**: Define contract for all transcription implementations (API or local)

**Attributes**:
- `provider_name: str` - Unique identifier ("openai", "groq", "faster-whisper")
- `is_available: bool` - Whether provider can be used (dependencies met, device available)

**Methods**:
```python
@abstractmethod
async def transcribe(
    self,
    audio_file: AudioFile,
    config: TranscriptionConfig
) -> TranscriptionResult:
    """Transcribe audio file using provider-specific implementation"""
    pass

@abstractmethod
def validate_config(self, config: TranscriptionConfig) -> None:
    """Validate provider-specific configuration"""
    pass

@abstractmethod
def get_required_dependencies(self) -> list[str]:
    """Return list of required package names"""
    pass
```

**Invariants**:
- `provider_name` must be unique across all provider implementations
- `is_available` must be checked before calling `transcribe()`
- `transcribe()` must return consistent TranscriptionResult format across all providers (FR-011)

**State Transitions**:
```
[Uninitialized] → validate_config() → [Ready]
[Ready] → transcribe() → [Processing] → [Complete]
[Ready] → (dependencies missing) → [Unavailable]
```

---

### 2. LocalModelConfiguration

**Purpose**: Configuration for local Whisper model inference

**Attributes**:
```python
model_name: str = "base"           # Model size (tiny, base, small, medium, large, large-v2, large-v3)
device: str = "cpu"                 # Compute device (cpu, cuda, mps)
compute_type: str = "int8"          # Precision (int8, int16, float16, float32)
beam_size: int = 5                  # Beam search width (1-10)
language: str | None = None         # Force language (None = auto-detect)
temperature: float = 0.0            # Sampling temperature (0.0 = greedy)
vad_filter: bool = False            # Voice activity detection filter
max_workers: int = 2                # Maximum concurrent jobs
cache_max_size_gb: float = 8.0      # Maximum model cache size in GB
download_root: Path = Path("~/.cache/sogon/models")  # Model storage directory
```

**Validation Rules**:
- `model_name` must be in VALID_MODELS = {"tiny", "base", "small", "medium", "large", "large-v2", "large-v3"}
- `device` must be in {"cpu", "cuda", "mps"}
- `compute_type` must match device capabilities:
  - CPU: int8, int16
  - CUDA: int8, float16, float32
  - MPS: float16, float32
- `beam_size` must be 1 ≤ beam_size ≤ 10
- `temperature` must be 0.0 ≤ temperature ≤ 1.0
- `max_workers` must be 1 ≤ max_workers ≤ 10
- `cache_max_size_gb` must be > 0

**Relationships**:
- Passed to FasterWhisperProvider on initialization
- Serialized to/from environment variables (SOGON_LOCAL_*)
- Serialized to/from CLI flags (--local-model, --device, etc.)

---

### 3. ModelManager

**Purpose**: Manage Whisper model lifecycle (download, load, cache, eviction)

**Attributes**:
```python
cache_dir: Path                      # Model storage directory
loaded_models: dict[ModelKey, WhisperModel]  # Currently loaded models
cache_max_size_gb: float             # Maximum cache size
model_sizes: dict[str, int]          # Model name → size in bytes
```

**Methods**:
```python
async def get_model(self, key: ModelKey) -> WhisperModel:
    """Get model from cache or load it (with auto-download)"""

async def download_model(self, model_name: str) -> Path:
    """Download model from Hugging Face with progress feedback"""

def evict_lru_model(self) -> None:
    """Remove least recently used model from cache"""

def get_cache_usage_gb(self) -> float:
    """Calculate current cache size in GB"""

def check_disk_space(self, model_name: str) -> bool:
    """Verify sufficient disk space before download (FR-005)"""
```

**Invariants**:
- Total cache size ≤ cache_max_size_gb
- LRU eviction maintains cache below size limit
- Models are validated after download (hash check)
- Download progress feedback provided via callback (FR-027)

**State Transitions**:
```
[Empty Cache] → download_model() → [Model Downloading] → [Model Cached]
[Model Cached] → get_model() → [Model Loaded] → (eviction) → [Empty Cache]
[Cache Full] → evict_lru_model() → [Space Available] → download_model()
```

---

### 4. ModelKey (Value Object)

**Purpose**: Immutable identifier for cached models

**Attributes**:
```python
model_name: str       # e.g., "base", "large-v2"
device: str           # e.g., "cuda", "cpu"
compute_type: str     # e.g., "float16", "int8"
```

**Invariants**:
- Immutable (frozen dataclass)
- Hashable (used as dict key)
- All attributes required

**Usage**:
```python
key = ModelKey(model_name="base", device="cuda", compute_type="float16")
model = model_manager.get_model(key)  # Cache lookup
```

---

### 5. FasterWhisperProvider (Concrete Implementation)

**Purpose**: Local Whisper model transcription using faster-whisper

**Attributes**:
```python
provider_name: str = "faster-whisper"
config: LocalModelConfiguration
model_manager: ModelManager
device_selector: DeviceSelector
semaphore: asyncio.Semaphore       # Concurrency control (FR-022)
```

**Methods**:
```python
async def transcribe(
    self,
    audio_file: AudioFile,
    config: TranscriptionConfig
) -> TranscriptionResult:
    """Transcribe using local Whisper model"""

def validate_config(self, config: TranscriptionConfig) -> None:
    """Validate local model configuration"""

def get_required_dependencies(self) -> list[str]:
    """Return ['faster-whisper', 'torch', 'huggingface-hub']"""

async def _monitor_resources(self) -> None:
    """Monitor RAM/VRAM and terminate if exhausted (FR-021)"""
```

**Relationships**:
- Implements TranscriptionProvider interface
- Composes ModelManager for model lifecycle
- Composes DeviceSelector for hardware detection

---

### 6. DeviceSelector

**Purpose**: Detect and validate compute devices

**Methods**:
```python
def get_available_device(self, preferred: str = "cpu") -> str:
    """
    Return best available device.
    Priority: preferred → cuda (if available) → cpu (fallback)
    """

def validate_device(self, device: str) -> bool:
    """Check if device is available on system (FR-007)"""

def get_device_memory_gb(self, device: str) -> float:
    """Get available memory for device (RAM for CPU, VRAM for GPU)"""

def get_compute_capabilities(self, device: str) -> dict[str, Any]:
    """Get device properties (CUDA version, cores, etc.)"""
```

**Validation Rules**:
- CUDA device requires torch.cuda.is_available() = True
- MPS device requires torch.backends.mps.is_available() = True
- CPU device always available (fallback)

---

### 7. TranscriptionConfig (Extended)

**Purpose**: Unified configuration for all transcription providers

**Existing Attributes** (from spec Key Entities):
```python
provider: str = "openai"                # Provider type
model: str = "whisper-1"               # Model name (provider-specific)
language: str | None = None            # Force language or auto-detect
temperature: float = 0.0               # Sampling temperature
```

**New Attributes** (for local models):
```python
local: LocalModelConfiguration | None = None  # Local model settings (if provider="faster-whisper")
```

**Validation**:
- If `provider == "faster-whisper"`, `local` must not be None
- If `provider in {"openai", "groq"}`, `local` is ignored

---

### 8. ResourceMonitor

**Purpose**: Track memory and resource usage during transcription

**Attributes**:
```python
check_interval_sec: float = 5.0      # How often to check resources
ram_threshold_percent: float = 90.0  # Alert threshold for RAM
vram_threshold_percent: float = 90.0 # Alert threshold for VRAM
```

**Methods**:
```python
def get_ram_usage() -> dict[str, float]:
    """Return {'used_gb', 'available_gb', 'percent'}"""

def get_vram_usage(device: str) -> dict[str, float]:
    """Return {'used_gb', 'available_gb', 'percent'}"""

def check_resources_available(self, min_ram_gb: float, min_vram_gb: float) -> bool:
    """Verify sufficient resources before starting transcription"""

async def monitor_during_transcription(self, callback: Callable) -> None:
    """Periodically check resources and call callback if exhausted (FR-021)"""
```

**Error Conditions**:
- Raise ResourceExhaustedError if RAM > 90% or VRAM > 90% (FR-021)
- Error message includes current usage and minimum requirements

---

## Entity Relationships

```
TranscriptionProvider (interface)
        ↑
        |
        |-- OpenAIProvider (existing)
        |-- GroqProvider (existing)
        |-- FasterWhisperProvider (new)
                |
                |-- ModelManager (composition)
                |       |
                |       |-- uses ModelKey for caching
                |       |-- downloads from HuggingFace
                |
                |-- DeviceSelector (composition)
                |       |
                |       |-- detects CUDA/MPS/CPU
                |
                |-- ResourceMonitor (composition)
                        |
                        |-- monitors RAM/VRAM

TranscriptionConfig (unified)
        |
        |-- contains LocalModelConfiguration (optional)

TranscriptionService (existing)
        |
        |-- uses TranscriptionProvider (dependency injection)
```

---

## Data Flow

### Local Transcription Flow

```
1. User Request
   ↓
2. TranscriptionService.transcribe(audio_file, config)
   ↓
3. ServiceContainer.get_provider(config.provider)
   → returns FasterWhisperProvider
   ↓
4. FasterWhisperProvider.transcribe(audio_file, config)
   ↓
5. DeviceSelector.validate_device(config.local.device)
   ↓
6. ResourceMonitor.check_resources_available(min_ram, min_vram)
   ↓
7. ModelManager.get_model(ModelKey)
   ├─ (cache hit) → return cached model
   └─ (cache miss) → ModelManager.download_model()
       ├─ check_disk_space()
       ├─ download from HuggingFace (with progress)
       └─ load model into memory
   ↓
8. model.transcribe(audio_file)
   ├─ ResourceMonitor.monitor_during_transcription()
   └─ (on resource exhaustion) → raise ResourceExhaustedError
   ↓
9. Format output as TranscriptionResult
   ↓
10. Return result (identical format to API providers per FR-011)
```

---

## Validation Matrix

| Entity | Validation Method | When Validated | Error Type |
|--------|-------------------|----------------|------------|
| LocalModelConfiguration | Pydantic validators | On initialization | ValidationError |
| ModelKey | Frozen dataclass | On creation | TypeError |
| Device availability | DeviceSelector.validate_device() | Before transcription | DeviceNotAvailableError |
| Disk space | ModelManager.check_disk_space() | Before download | InsufficientDiskSpaceError |
| Memory availability | ResourceMonitor.check_resources_available() | Before + during transcription | ResourceExhaustedError |
| Model integrity | Hash verification | After download | ModelCorruptionError |
| Config consistency | TranscriptionConfig validators | On request | ConfigurationError |

---

## Storage Schema

### Model Cache Directory Structure

```
~/.cache/sogon/models/
├── faster-whisper-tiny/
│   ├── model.bin
│   ├── config.json
│   └── vocabulary.json
├── faster-whisper-base/
│   ├── model.bin
│   ├── config.json
│   └── vocabulary.json
└── faster-whisper-large-v3/
    ├── model.bin
    ├── config.json
    └── vocabulary.json
```

### Model Metadata (in-memory)

```python
{
    "model_name": "base",
    "size_bytes": 149_000_000,
    "download_date": "2025-10-17T10:30:00Z",
    "last_accessed": "2025-10-17T14:25:00Z",
    "checksum_sha256": "abc123...",
    "huggingface_repo": "Systran/faster-whisper-base"
}
```

---

## Error Handling

### Error Hierarchy

```
TranscriptionError (base)
├── ProviderNotAvailableError (dependencies missing)
├── DeviceNotAvailableError (CUDA/MPS not found)
├── InsufficientDiskSpaceError (not enough storage)
├── ResourceExhaustedError (RAM/VRAM exceeded)
├── ModelDownloadError (network/HF issues)
├── ModelCorruptionError (hash mismatch)
└── ConfigurationError (invalid settings)
```

### Error Messages (FR-025, FR-009)

Each error must include:
- Clear description of what went wrong
- Current state (e.g., "Available: 1.2GB, Required: 2.5GB")
- Actionable resolution (e.g., "Free up disk space or use smaller model")
- Documentation link (FR-009)

---

## Testing Implications

### Contract Tests (Per User Directive: Tests First)

```python
# tests/contract/test_transcription_provider_contract.py
@pytest.mark.parametrize("provider_class", [
    OpenAIProvider,
    GroqProvider,
    FasterWhisperProvider
])
def test_provider_implements_contract(provider_class):
    """All providers must implement TranscriptionProvider interface"""
    assert issubclass(provider_class, TranscriptionProvider)
    assert hasattr(provider_class, 'transcribe')
    assert hasattr(provider_class, 'validate_config')
    assert hasattr(provider_class, 'get_required_dependencies')

def test_provider_output_format_consistency():
    """All providers must return identical TranscriptionResult format (FR-011)"""
    # Test with mock audio file
    # Assert all providers return same schema
```

### Unit Tests

```python
# tests/unit/test_model_manager.py
@pytest.mark.asyncio
async def test_model_manager_lru_eviction():
    """When cache exceeds max_size, evict LRU model (FR-024)"""

def test_model_manager_disk_space_check():
    """Verify disk space checked before download (FR-005)"""

# tests/unit/test_device_selector.py
def test_device_selector_cuda_detection():
    """Detect CUDA availability correctly (FR-007)"""

# tests/unit/test_resource_monitor.py
def test_resource_monitor_exhaustion_detection():
    """Raise error when RAM/VRAM > 90% (FR-021)"""
```

### Integration Tests

```python
# tests/integration/test_local_transcription_e2e.py
@pytest.mark.integration
@pytest.mark.asyncio
async def test_local_transcription_full_workflow():
    """
    End-to-end test:
    1. Configure local provider
    2. Transcribe sample audio
    3. Verify output format matches API providers
    4. Verify model cached for reuse
    """
```

---

## Data Model Complete

All entities defined with attributes, relationships, validation rules, and state transitions. Ready for contract generation.
