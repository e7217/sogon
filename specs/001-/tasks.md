# Implementation Tasks: Local Whisper Model Support

**Feature**: Local Whisper model inference capability
**Branch**: `001-`
**Date**: 2025-10-17
**Generated From**: [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

---

## Task Execution Principles

**TDD Strict**: Write ALL tests before ANY implementation
**Interfaces First**: Define contracts before concrete classes
**Parallelizable Tasks**: Marked with [P] for concurrent execution
**Validation Gates**: Each phase must pass tests before next phase

---

## Phase 3.1: Setup (3 tasks) ✅

### Task 1: Project structure setup ✅
**Type**: Setup
**Priority**: Critical
**Parallelizable**: No
**Status**: Complete

**Objective**: Create directory structure for local model feature

**Actions**:
1. Create `sogon/providers/local/` directory
2. Create `sogon/providers/local/__init__.py`
3. Create `sogon/models/local_config.py` for configuration models
4. Create `sogon/services/model_management/` directory
5. Create test directories:
   - `tests/contract/providers/`
   - `tests/unit/providers/local/`
   - `tests/unit/services/model_management/`
   - `tests/integration/providers/`

**Acceptance**:
- All directories created
- `__init__.py` files in place
- No import errors when importing new directories

---

### Task 2: Add dependencies to pyproject.toml ✅
**Type**: Setup
**Priority**: Critical
**Parallelizable**: No
**Status**: Complete

**Objective**: Add local model dependencies with optional extras group

**Actions**:
1. Add `[local]` extras group to `pyproject.toml`:
   ```toml
   [project.optional-dependencies]
   local = [
       "faster-whisper>=1.0.0",
       "torch>=2.0.0",
       "torchaudio>=2.0.0",
       "huggingface-hub>=0.19.0",
       "psutil>=5.9.0"
   ]
   ```
2. Document installation: `pip install sogon[local]`

**Acceptance**:
- `pyproject.toml` valid and parseable
- `pip install -e .[local]` succeeds
- Dependencies installable without conflicts

---

### Task 3: Create test fixtures and mock audio files ✅
**Type**: Setup
**Priority**: High
**Parallelizable**: [P]
**Status**: Complete

**Objective**: Create reusable test fixtures for audio files and configs

**Actions**:
1. Create `tests/fixtures/audio.py`:
   - Mock AudioFile objects
   - Sample audio data generators
   - Duration/format helpers
2. Create `tests/fixtures/test_audio.mp3` (small sample file)
3. Create `tests/fixtures/configs.py`:
   - Valid LocalModelConfiguration samples
   - Invalid config examples for validation testing

**Acceptance**:
- Fixtures importable: `from tests.fixtures import audio, configs`
- Mock audio files <1MB total
- Config fixtures cover all validation scenarios

---

## Phase 3.2: Tests First - TDD (20 tasks) [P] ✅

### Task 4: Write TranscriptionProvider interface contract tests [P] ✅
**Type**: Contract Test
**Priority**: Critical
**Parallelizable**: [P]
**Contract**: [transcription_provider_interface.py](./contracts/transcription_provider_interface.py)
**Status**: Complete

**Objective**: Validate all providers implement TranscriptionProvider ABC correctly

**Test File**: `tests/contract/providers/test_transcription_provider_contract.py`

**Test Cases**:
1. `test_provider_implements_interface()`:
   - Verify OpenAIProvider, GroqProvider, FasterWhisperProvider inherit TranscriptionProvider
   - Verify all abstract methods implemented
2. `test_provider_output_format_consistency()`:
   - Transcribe same mock audio with all providers
   - Assert identical TranscriptionResult schema (FR-011)
   - Assert timestamp formats match (FR-012)
3. `test_provider_error_handling()`:
   - Trigger each error condition per provider
   - Assert error messages include actionable info (FR-025, FR-009)
   - Assert error types are correct subclasses
4. `test_provider_availability_check()`:
   - Mock missing dependencies
   - Assert is_available returns False
   - Assert transcribe() raises ProviderNotAvailableError
5. `test_provider_config_validation()`:
   - Pass invalid configs to each provider
   - Assert validate_config() raises with clear messages

**Acceptance**:
- All 5 test cases implemented and failing (no implementation yet)
- pytest runs successfully with expected failures
- Code coverage: 100% of contract specification tested

---

### Task 5: Write LocalModelConfiguration schema validation tests [P] ✅
**Type**: Contract Test
**Priority**: Critical
**Parallelizable**: [P]
**Contract**: [local_model_config_schema.py](./contracts/local_model_config_schema.py)
**Status**: Complete

**Objective**: Validate LocalModelConfiguration Pydantic schema enforces all validation rules

**Test File**: `tests/contract/models/test_local_model_config_contract.py`

**Test Cases**:
1. `test_valid_configs()`:
   - Create configs with all valid model/device/compute_type combinations
   - Assert no ValidationError raised
2. `test_invalid_model_name()`:
   - Try model_name="invalid"
   - Assert ValueError with message listing valid models
3. `test_invalid_device()`:
   - Try device="tpu"
   - Assert ValueError with message listing valid devices
4. `test_compute_type_device_mismatch()`:
   - Try compute_type="float16" with device="cpu"
   - Try compute_type="int8" with device="mps"
   - Assert ValueError explaining device-compute_type compatibility
5. `test_resource_estimates()`:
   - Verify get_model_size_estimate_gb() returns correct values for each model
   - Verify get_min_ram_gb() meets requirements from data-model.md
   - Verify get_min_vram_gb() for GPU vs CPU
6. `test_environment_variable_parsing()`:
   - Mock env vars: SOGON_LOCAL_MODEL_NAME=small
   - Create config from env
   - Assert config.model_name == "small"
7. `test_cli_flag_parsing()`:
   - Simulate CLI args: --local-model large --device cuda
   - Parse into config
   - Assert correct config created

**Acceptance**:
- All 7 test cases implemented and failing
- Covers all validation rules from contract
- pytest runs with expected failures

---

### Task 6: Implement TranscriptionProvider ABC (interface only) [P] ✅
**Type**: Entity Model
**Priority**: Critical
**Parallelizable**: [P]
**Entity**: TranscriptionProvider (data-model.md #1)
**Status**: Complete

**Objective**: Create abstract base class defining provider contract

**Implementation File**: `sogon/providers/base.py`

**Requirements**:
1. Import from abc: ABC, abstractmethod
2. Define abstract properties:
   - `provider_name: str`
   - `is_available: bool`
3. Define abstract methods:
   - `async def transcribe(audio_file, config) -> TranscriptionResult`
   - `def validate_config(config) -> None`
   - `def get_required_dependencies() -> list[str]`
   - `async def transcribe_stream(audio_file, config) -> AsyncIterator[dict]`
4. Add comprehensive docstrings with examples per contract

**Acceptance**:
- Class defined with all abstract methods
- Cannot instantiate directly (raises TypeError)
- Docstrings match contract specification
- Task 4 contract tests begin passing (interface checks)

---

### Task 7: Implement LocalModelConfiguration Pydantic model [P] ✅
**Type**: Entity Model
**Priority**: Critical
**Parallelizable**: [P]
**Entity**: LocalModelConfiguration (data-model.md #2)
**Status**: Complete

**Objective**: Create validated configuration model with all validation rules

**Implementation File**: `sogon/models/local_config.py`

**Requirements**:
1. Pydantic BaseModel with all fields from contract:
   - model_name, device, compute_type, beam_size, language, temperature, vad_filter
   - max_workers, cache_max_size_gb, download_root
2. Implement all field validators:
   - validate_model_name, validate_device, validate_compute_type, validate_language
   - validate_download_root
3. Implement helper methods:
   - get_model_size_estimate_gb()
   - get_min_ram_gb()
   - get_min_vram_gb()
4. Add VALID_MODELS, VALID_DEVICES, DEVICE_COMPUTE_TYPES constants

**Acceptance**:
- Task 5 contract tests pass (all validation scenarios)
- Model serializable to/from JSON and env vars
- Error messages actionable per FR-025

---

### Task 8: Implement ModelKey value object [P] ✅
**Type**: Entity Model
**Priority**: High
**Parallelizable**: [P]
**Entity**: ModelKey (data-model.md #4)
**Status**: Complete

**Objective**: Create immutable hashable key for model caching

**Implementation File**: `sogon/services/model_management/model_key.py`

**Requirements**:
1. Frozen dataclass with fields: model_name, device, compute_type
2. Implement __hash__ and __eq__ for dict key usage
3. Implement __repr__ for debugging
4. Add type hints for all fields

**Acceptance**:
- Immutable (frozen=True)
- Hashable (can use as dict key)
- Two identical ModelKeys compare equal
- Repr shows all field values

---

### Task 9: Write ModelManager unit tests (TDD) [P] ✅
**Type**: Unit Test
**Priority**: Critical
**Parallelizable**: [P]
**Entity**: ModelManager (data-model.md #3)
**Status**: Complete

**Objective**: Test model download, caching, and LRU eviction logic

**Test File**: `tests/unit/services/model_management/test_model_manager.py`

**Test Cases**:
1. `test_get_model_cache_hit()`:
   - Mock model already cached
   - Assert get_model() returns without download
2. `test_get_model_cache_miss_downloads()`:
   - Mock model not cached
   - Assert download_model() called with progress callback
3. `test_download_model_checks_disk_space()`:
   - Mock insufficient disk space (<500MB)
   - Assert InsufficientDiskSpaceError raised (FR-005)
4. `test_download_model_validates_checksum()`:
   - Mock corrupted download (bad checksum)
   - Assert ModelCorruptionError raised
5. `test_lru_eviction_when_cache_full()`:
   - Fill cache to max_size_gb
   - Add new model
   - Assert least recently used model evicted (FR-024)
6. `test_get_cache_usage_gb_accurate()`:
   - Add 3 models to cache
   - Assert get_cache_usage_gb() matches sum of model sizes
7. `test_concurrent_downloads_same_model()`:
   - Start 2 concurrent get_model() for same ModelKey
   - Assert only 1 download occurs (locking)

**Acceptance**:
- All 7 test cases implemented and failing
- Mocked: huggingface-hub, disk operations, file I/O
- pytest runs with expected failures

---

### Task 10: Write DeviceSelector unit tests (TDD) [P] ✅
**Type**: Unit Test
**Priority**: High
**Parallelizable**: [P]
**Entity**: DeviceSelector (data-model.md #6)
**Status**: Complete

**Objective**: Test device detection and validation logic

**Test File**: `tests/unit/services/model_management/test_device_selector.py`

**Test Cases**:
1. `test_get_available_device_prefers_requested()`:
   - Request device="cuda" with CUDA available
   - Assert returns "cuda"
2. `test_get_available_device_fallback_to_cpu()`:
   - Request device="cuda" without CUDA
   - Assert returns "cpu" (fallback)
3. `test_validate_device_cuda_available()`:
   - Mock torch.cuda.is_available() = True
   - Assert validate_device("cuda") returns True
4. `test_validate_device_cuda_unavailable()`:
   - Mock torch.cuda.is_available() = False
   - Assert validate_device("cuda") returns False (FR-007)
5. `test_get_device_memory_gb_cpu()`:
   - Mock psutil.virtual_memory()
   - Assert get_device_memory_gb("cpu") returns RAM in GB
6. `test_get_device_memory_gb_cuda()`:
   - Mock torch.cuda.get_device_properties()
   - Assert get_device_memory_gb("cuda") returns VRAM in GB
7. `test_get_compute_capabilities_cuda()`:
   - Mock CUDA device properties
   - Assert dict contains: version, cores, memory

**Acceptance**:
- All 7 test cases implemented and failing
- Mocked: torch.cuda, torch.backends.mps, psutil
- pytest runs with expected failures

---

### Task 11: Write ResourceMonitor unit tests (TDD) [P] ✅
**Type**: Unit Test
**Priority**: High
**Parallelizable**: [P]
**Entity**: ResourceMonitor (data-model.md #8)
**Status**: Complete

**Objective**: Test memory monitoring and exhaustion detection

**Test File**: `tests/unit/services/model_management/test_resource_monitor.py`

**Test Cases**:
1. `test_get_ram_usage_returns_dict()`:
   - Mock psutil.virtual_memory()
   - Assert returns dict with keys: used_gb, available_gb, percent
2. `test_get_vram_usage_cuda()`:
   - Mock torch.cuda.memory_allocated()
   - Assert returns dict with VRAM usage
3. `test_check_resources_available_sufficient()`:
   - Mock 16GB RAM available, request 8GB min
   - Assert check_resources_available() returns True
4. `test_check_resources_available_insufficient()`:
   - Mock 4GB RAM available, request 8GB min
   - Assert check_resources_available() returns False
5. `test_monitor_raises_when_ram_exceeds_90_percent()`:
   - Mock RAM usage at 92%
   - Assert monitor_during_transcription() raises ResourceExhaustedError (FR-021)
6. `test_monitor_raises_when_vram_exceeds_90_percent()`:
   - Mock VRAM usage at 95%
   - Assert raises ResourceExhaustedError with actionable message
7. `test_monitor_callback_called_on_exhaustion()`:
   - Mock resource exhaustion
   - Assert callback called with error details

**Acceptance**:
- All 7 test cases implemented and failing
- Mocked: psutil, torch.cuda memory APIs
- pytest runs with expected failures

---

### Task 12: Write FasterWhisperProvider unit tests (TDD) [P] ✅
**Type**: Unit Test
**Priority**: Critical
**Parallelizable**: [P]
**Entity**: FasterWhisperProvider (data-model.md #5)
**Status**: Complete

**Objective**: Test local transcription provider implementation

**Test File**: `tests/unit/providers/local/test_faster_whisper_provider.py`

**Test Cases**:
1. `test_provider_name_is_faster_whisper()`:
   - Assert provider.provider_name == "faster-whisper"
2. `test_is_available_true_when_dependencies_installed()`:
   - Mock faster_whisper importable
   - Assert provider.is_available == True
3. `test_is_available_false_when_dependencies_missing()`:
   - Mock ImportError on faster_whisper
   - Assert provider.is_available == False
4. `test_get_required_dependencies_returns_list()`:
   - Assert returns ['faster-whisper', 'torch', 'huggingface-hub', 'psutil']
5. `test_validate_config_raises_when_local_config_missing()`:
   - Pass config with local=None
   - Assert ConfigurationError raised
6. `test_transcribe_checks_device_available()`:
   - Request device="cuda" unavailable
   - Assert DeviceNotAvailableError raised (FR-009)
7. `test_transcribe_checks_resources_before_loading_model()`:
   - Mock insufficient RAM
   - Assert ResourceExhaustedError raised before model load
8. `test_transcribe_loads_model_via_model_manager()`:
   - Mock ModelManager.get_model()
   - Assert get_model() called with correct ModelKey
9. `test_transcribe_returns_transcription_result()`:
   - Mock successful transcription
   - Assert returns TranscriptionResult with text, segments, metadata
10. `test_transcribe_respects_max_workers_concurrency()`:
    - Start 3 transcriptions with max_workers=2
    - Assert only 2 run concurrently (asyncio.Semaphore)
11. `test_transcribe_stream_yields_segments()`:
    - Mock streaming transcription
    - Assert transcribe_stream() yields dicts with start, end, text

**Acceptance**:
- All 11 test cases implemented and failing
- Mocked: faster_whisper, ModelManager, DeviceSelector, ResourceMonitor
- pytest runs with expected failures

---

### Task 13-15: Write integration test files [P] ✅
**Type**: Integration Test
**Priority**: High
**Parallelizable**: [P]
**Status**: Complete

**Objective**: Write E2E integration tests based on quickstart.md scenarios

---

#### Task 13: Write E2E local transcription test [P] ✅
**Test File**: `tests/integration/providers/test_local_transcription_e2e.py`
**Status**: Complete

**Test Cases** (from quickstart.md Test 1):
1. `test_local_transcription_produces_valid_output()`:
   - Transcribe test_audio.mp3 with --provider faster-whisper
   - Assert output file created (local.srt)
   - Assert SRT format valid
2. `test_local_output_format_matches_api_format()`:
   - Transcribe same audio with faster-whisper and openai
   - Assert both produce valid SRT with same structure (FR-011)

**Acceptance**:
- Tests implemented and skipped with `@pytest.mark.skip("No implementation yet")`
- Requires actual test audio file (~5 seconds)
- pytest collects tests successfully

---

#### Task 14: Write backward compatibility test [P] ✅
**Test File**: `tests/integration/providers/test_backward_compatibility.py`
**Status**: Complete

**Test Cases** (from quickstart.md Test 2):
1. `test_existing_api_workflow_unchanged()`:
   - Run `sogon transcribe audio.mp3` (default OpenAI)
   - Assert no errors, warnings, or behavior changes (FR-017)
2. `test_local_provider_opt_in_only()`:
   - Verify local dependencies NOT required for basic install
   - Import sogon succeeds without faster-whisper

**Acceptance**:
- Tests verify zero impact on existing users
- Tests skipped until implementation
- pytest collects tests successfully

---

#### Task 15: Write GPU acceleration and concurrent job tests [P] ✅
**Test File**: `tests/integration/providers/test_gpu_and_concurrency.py`
**Status**: Complete

**Test Cases** (from quickstart.md Tests 5-7):
1. `test_gpu_device_detection_error_when_unavailable()`:
   - Request --device cuda on CPU-only machine
   - Assert DeviceNotAvailableError with actionable message (FR-009)
2. `test_model_caching_reuses_downloaded_model()`:
   - First transcription: model downloads
   - Second transcription: model loaded from cache (FR-024)
   - Assert second transcription starts faster
3. `test_concurrent_job_limiting_respects_max_workers()`:
   - Start 3 transcriptions with max_workers=2
   - Assert only 2 run concurrently (FR-022, FR-023)

**Acceptance**:
- Tests skipped until implementation
- GPU test requires CUDA detection mocking
- pytest collects tests successfully

---

## Phase 3.3: Core Implementation (8 tasks) - Sequential ✅

### Task 16: Implement ModelManager ✅
**Type**: Implementation
**Priority**: Critical
**Depends On**: Tasks 8, 9
**Entity**: ModelManager (data-model.md #3)
**Status**: Complete

**Objective**: Implement model download, caching, and LRU eviction

**Implementation File**: `sogon/services/model_management/model_manager.py`

**Requirements**:
1. Implement `__init__(cache_dir, cache_max_size_gb)`
2. Implement `async def get_model(key: ModelKey) -> WhisperModel`:
   - Check cache: if exists and valid → return
   - Else: await download_model() → load → cache → return
3. Implement `async def download_model(model_name: str) -> Path`:
   - Check disk space via check_disk_space()
   - Download from Hugging Face with progress callback (FR-027)
   - Validate checksum
   - Return path to model directory
4. Implement `def evict_lru_model() -> None`:
   - Track access times for each cached model
   - Remove least recently used when cache_usage > cache_max_size_gb
5. Implement `def get_cache_usage_gb() -> float`:
   - Sum sizes of all cached model directories
6. Implement `def check_disk_space(model_name: str) -> bool`:
   - Use shutil.disk_usage()
   - Compare available space vs estimated model size + 500MB buffer
   - Return False if insufficient (FR-005)

**Acceptance**:
- Task 9 unit tests pass
- LRU eviction working correctly
- Downloads progress visible via callback
- Disk space check prevents downloads when insufficient

---

### Task 17: Implement DeviceSelector ✅
**Type**: Implementation
**Priority**: High
**Depends On**: Task 10
**Entity**: DeviceSelector (data-model.md #6)
**Status**: Complete

**Objective**: Implement hardware detection and validation

**Implementation File**: `sogon/services/model_management/device_selector.py`

**Requirements**:
1. Implement `def get_available_device(preferred: str = "cpu") -> str`:
   - If preferred available → return preferred
   - Else if CUDA available → return "cuda"
   - Else → return "cpu" (fallback)
2. Implement `def validate_device(device: str) -> bool`:
   - CPU: always True
   - CUDA: torch.cuda.is_available()
   - MPS: torch.backends.mps.is_available()
3. Implement `def get_device_memory_gb(device: str) -> float`:
   - CPU: psutil.virtual_memory().available / 1024^3
   - CUDA: torch.cuda.get_device_properties().total_memory / 1024^3
   - MPS: psutil.virtual_memory().available / 1024^3
4. Implement `def get_compute_capabilities(device: str) -> dict`:
   - CUDA: version, cores, name from torch.cuda.get_device_properties()
   - CPU/MPS: cores from psutil.cpu_count()

**Acceptance**:
- Task 10 unit tests pass
- Correct detection on CPU-only, CUDA, and MPS hardware
- Fallback to CPU when preferred device unavailable

---

### Task 18: Implement ResourceMonitor ✅
**Type**: Implementation
**Priority**: High
**Depends On**: Task 11
**Entity**: ResourceMonitor (data-model.md #8)
**Status**: Complete

**Objective**: Implement memory monitoring and exhaustion detection

**Implementation File**: `sogon/services/model_management/resource_monitor.py`

**Requirements**:
1. Implement `__init__(check_interval_sec=5.0, ram_threshold=90.0, vram_threshold=90.0)`
2. Implement `def get_ram_usage() -> dict[str, float]`:
   - Use psutil.virtual_memory()
   - Return: {used_gb, available_gb, percent}
3. Implement `def get_vram_usage(device: str) -> dict[str, float]`:
   - Use torch.cuda.memory_allocated() and total_memory()
   - Return: {used_gb, available_gb, percent}
4. Implement `def check_resources_available(min_ram_gb: float, min_vram_gb: float = 0) -> bool`:
   - Check RAM: available >= min_ram_gb
   - If GPU: check VRAM >= min_vram_gb
   - Return True only if both sufficient
5. Implement `async def monitor_during_transcription(callback: Callable) -> None`:
   - Periodically check RAM/VRAM every check_interval_sec
   - If RAM > ram_threshold OR VRAM > vram_threshold:
     - Call callback with error details
     - Raise ResourceExhaustedError (FR-021)

**Acceptance**:
- Task 11 unit tests pass
- Raises ResourceExhaustedError when RAM/VRAM > 90%
- Error messages include current usage and minimum requirements (FR-025)

---

### Task 19: Implement FasterWhisperProvider ✅
**Type**: Implementation
**Priority**: Critical
**Depends On**: Tasks 6, 7, 16, 17, 18
**Entity**: FasterWhisperProvider (data-model.md #5)
**Status**: Complete

**Objective**: Implement local transcription provider with all components integrated

**Implementation File**: `sogon/providers/local/faster_whisper_provider.py`

**Requirements**:
1. Inherit from TranscriptionProvider (Task 6)
2. Implement `__init__(config: LocalModelConfiguration)`:
   - Initialize ModelManager, DeviceSelector, ResourceMonitor
   - Create asyncio.Semaphore(max_workers) for concurrency control
3. Implement `@property provider_name -> str`: return "faster-whisper"
4. Implement `@property is_available -> bool`:
   - Try importing faster_whisper
   - Return True if importable, False otherwise
5. Implement `def validate_config(config: TranscriptionConfig) -> None`:
   - Verify config.provider == "faster-whisper"
   - Verify config.local is not None
   - Call LocalModelConfiguration validators
6. Implement `def get_required_dependencies() -> list[str]`:
   - Return ['faster-whisper', 'torch', 'huggingface-hub', 'psutil']
7. Implement `async def transcribe(audio_file, config) -> TranscriptionResult`:
   - Acquire semaphore (concurrency control)
   - Validate device available via DeviceSelector
   - Check resources available via ResourceMonitor
   - Load model via ModelManager.get_model()
   - Start resource monitoring task
   - Transcribe using faster_whisper.WhisperModel
   - Format output as TranscriptionResult (FR-011)
   - Release semaphore
8. Implement `async def transcribe_stream(audio_file, config) -> AsyncIterator[dict]`:
   - Similar flow but yield segments as they complete

**Acceptance**:
- Task 12 unit tests pass
- Task 13 E2E integration test passes
- Respects max_workers concurrency limit
- Raises appropriate errors with actionable messages

---

### Task 20: Implement error classes ✅
**Type**: Implementation
**Priority**: High
**Depends On**: Task 6
**Status**: Complete

**Objective**: Create error hierarchy for local model operations

**Implementation File**: `sogon/exceptions.py` (extend existing)

**Requirements**:
1. Add to existing TranscriptionError hierarchy:
   - `ProviderNotAvailableError` (dependencies missing)
   - `DeviceNotAvailableError` (CUDA/MPS not found)
   - `InsufficientDiskSpaceError` (not enough storage)
   - `ResourceExhaustedError` (RAM/VRAM exceeded)
   - `ModelDownloadError` (network/HF issues)
   - `ModelCorruptionError` (hash mismatch)
   - `ConfigurationError` (invalid settings) - may already exist
2. Each error must include:
   - Clear description of what went wrong
   - Current state (e.g., "Available: 1.2GB, Required: 2.5GB")
   - Actionable resolution (e.g., "Free up disk space or use smaller model")

**Acceptance**:
- All error classes defined with comprehensive docstrings
- Error messages meet FR-025 (actionable) and FR-009 (clear)
- Unit tests can import and raise all error types

---

### Task 21: Update TranscriptionConfig model ✅
**Type**: Implementation
**Priority**: High
**Depends On**: Task 7
**Status**: Complete

**Objective**: Extend existing TranscriptionConfig to support local model config

**Implementation File**: `sogon/models/transcription.py` (extend existing)

**Requirements**:
1. Add optional field to existing TranscriptionConfig:
   ```python
   local: LocalModelConfiguration | None = None
   ```
2. Add validator:
   ```python
   @field_validator("local")
   @classmethod
   def validate_local_config(cls, v, info):
       provider = info.data.get("provider")
       if provider == "faster-whisper" and v is None:
           raise ValueError("local config required when provider='faster-whisper'")
       return v
   ```
3. Ensure backward compatibility: existing configs without `local` field remain valid

**Acceptance**:
- Existing TranscriptionConfig usage unaffected (FR-017)
- Validation enforces local config when provider="faster-whisper"
- Can serialize/deserialize configs with local field

---

### Task 22: Implement environment variable parsing ✅
**Type**: Implementation
**Priority**: Medium
**Depends On**: Task 7
**Status**: Complete

**Objective**: Parse SOGON_LOCAL_* environment variables into LocalModelConfiguration

**Implementation File**: `sogon/config.py` (extend existing)

**Requirements**:
1. Add env var parsing for:
   - `SOGON_LOCAL_MODEL_NAME` → model_name
   - `SOGON_LOCAL_DEVICE` → device
   - `SOGON_LOCAL_COMPUTE_TYPE` → compute_type
   - `SOGON_LOCAL_BEAM_SIZE` → beam_size
   - `SOGON_LOCAL_LANGUAGE` → language
   - `SOGON_LOCAL_TEMPERATURE` → temperature
   - `SOGON_LOCAL_VAD_FILTER` → vad_filter (bool)
   - `SOGON_LOCAL_MAX_WORKERS` → max_workers
   - `SOGON_LOCAL_CACHE_MAX_SIZE_GB` → cache_max_size_gb
   - `SOGON_LOCAL_DOWNLOAD_ROOT` → download_root
2. Create function `def parse_local_config_from_env() -> LocalModelConfiguration | None`:
   - Return None if no SOGON_LOCAL_* vars set
   - Return validated config if vars present
3. Integrate into existing config loading flow

**Acceptance**:
- quickstart.md Test 3 scenario works (env var configuration)
- Invalid env var values raise ValidationError with clear message
- Env vars override defaults but CLI flags override env vars

---

### Task 23: Add CLI flags for local model configuration ✅
**Type**: Implementation
**Priority**: High
**Depends On**: Task 7, 22
**Status**: Complete

**Objective**: Add Typer CLI flags for local model options

**Implementation File**: `sogon/cli/transcribe.py` (extend existing command)

**Requirements**:
1. Add CLI options to `transcribe` command:
   ```python
   --local-model TEXT        # Model name (tiny, base, small, medium, large, large-v2, large-v3)
   --device TEXT             # Device (cpu, cuda, mps)
   --compute-type TEXT       # Compute type (int8, int16, float16, float32)
   --beam-size INTEGER       # Beam search width (1-10)
   --language TEXT           # Force language (ISO 639-1 code)
   --temperature FLOAT       # Sampling temperature (0.0-1.0)
   --vad-filter              # Enable voice activity detection
   --max-workers INTEGER     # Max concurrent jobs (1-10)
   --cache-max-size-gb FLOAT # Max cache size in GB
   ```
2. Build LocalModelConfiguration from CLI args
3. Priority: CLI flags > env vars > defaults
4. Add validation: raise typer.BadParameter for invalid values

**Acceptance**:
- All flags work individually and in combination
- quickstart.md examples run successfully
- `sogon transcribe --help` shows new flags with descriptions
- Invalid flag values show helpful error messages

---

## Phase 3.4: Integration (4 tasks) - Sequential ✅

### Task 24: Wire FasterWhisperProvider into ServiceContainer ✅
**Type**: Integration
**Priority**: Critical
**Depends On**: Task 19
**Status**: Complete

**Objective**: Register FasterWhisperProvider in dependency injection container

**Implementation File**: `sogon/services/container.py` (extend existing)

**Requirements**:
1. Add FasterWhisperProvider to provider registry:
   ```python
   PROVIDERS = {
       "openai": OpenAIProvider,
       "groq": GroqProvider,
       "faster-whisper": FasterWhisperProvider,  # NEW
   }
   ```
2. Update `get_provider(provider_name: str)` method:
   - Return FasterWhisperProvider instance when provider_name="faster-whisper"
   - Handle ProviderNotAvailableError if dependencies missing
3. Update provider availability checking:
   - Check is_available before returning provider instance

**Acceptance**:
- `container.get_provider("faster-whisper")` returns FasterWhisperProvider
- Existing providers (OpenAI, Groq) unaffected (FR-017)
- Error raised with helpful message if faster-whisper dependencies missing

---

### Task 25: Update TranscriptionService to use provider pattern ✅
**Type**: Integration
**Priority**: High
**Depends On**: Task 24
**Status**: Complete

**Objective**: Ensure TranscriptionService works with all providers including FasterWhisperProvider

**Implementation File**: `sogon/services/transcription.py` (verify/update)

**Requirements**:
1. Verify TranscriptionService uses provider abstraction:
   ```python
   provider = container.get_provider(config.provider)
   result = await provider.transcribe(audio_file, config)
   ```
2. If provider-specific logic exists, refactor to use polymorphism
3. Ensure identical output format regardless of provider (FR-011)
4. Maintain backward compatibility with existing API-based workflows

**Acceptance**:
- Task 13 E2E test passes (local transcription works end-to-end)
- Task 14 backward compatibility test passes (existing workflows unchanged)
- All providers produce identical TranscriptionResult format

---

### Task 26: Add provider availability check to CLI ✅
**Type**: Integration
**Priority**: Medium
**Depends On**: Tasks 23, 24
**Status**: Complete

**Objective**: Show helpful error when local provider requested but dependencies missing

**Implementation File**: `sogon/cli/transcribe.py`

**Requirements**:
1. Before transcription, check provider availability:
   ```python
   provider = container.get_provider(config.provider)
   if not provider.is_available:
       deps = provider.get_required_dependencies()
       raise ProviderNotAvailableError(
           f"Provider '{config.provider}' not available.\n"
           f"Missing dependencies: {', '.join(deps)}\n"
           f"Install with: pip install sogon[local]"
       )
   ```
2. Ensure error message actionable per FR-009

**Acceptance**:
- When faster-whisper not installed, shows clear install instructions
- Error message includes `pip install sogon[local]` command
- Does not affect API-based providers (OpenAI, Groq)

---

### Task 27: Integration test validation ✅
**Type**: Integration
**Priority**: High
**Depends On**: Tasks 24, 25, 26
**Status**: Complete

**Objective**: Run and validate all integration tests pass

**Actions**:
1. Run `pytest tests/integration/`
2. Verify all tests pass:
   - test_local_transcription_e2e.py
   - test_backward_compatibility.py
   - test_gpu_and_concurrency.py
3. If any test fails:
   - Investigate root cause
   - Fix implementation issue
   - Re-run tests until all pass

**Acceptance**:
- All integration tests pass
- No test skips remaining (all @pytest.mark.skip removed)
- Test coverage for local provider ≥80%

---

## Phase 3.5: Polish & Documentation (4 tasks) [P] ✅

### Task 28: Update README with local model section [P] ✅
**Type**: Documentation
**Priority**: High
**Parallelizable**: [P]
**Status**: Complete

**Objective**: Document local model feature in project README

**Implementation File**: `README.md`

**Requirements**:
1. Add "Local Model Support" section after installation:
   - Installation with local extras: `pip install sogon[local]`
   - Basic usage example
   - GPU acceleration example
   - Environment variable configuration
   - Link to quickstart.md for full guide
2. Update feature list to include local transcription
3. Add performance benchmarks table (from quickstart.md)
4. Add troubleshooting section for common issues

**Acceptance**:
- README includes local model installation and usage
- Examples are copy-pasteable and working
- Links to additional documentation correct

---

### Task 29: Create CHANGELOG entry [P] ✅
**Type**: Documentation
**Priority**: Medium
**Parallelizable**: [P]
**Status**: Complete

**Objective**: Document feature in CHANGELOG

**Implementation File**: `CHANGELOG.md` (or create if missing)

**Requirements**:
1. Add entry for version where feature lands:
   ```markdown
   ## [X.Y.0] - 2025-MM-DD

   ### Added
   - Local Whisper model inference support via faster-whisper
   - Support for CPU, CUDA GPU, and Apple Silicon MPS acceleration
   - Model caching with LRU eviction policy
   - Concurrent transcription with configurable max workers
   - New CLI flags: --local-model, --device, --compute-type, etc.
   - Optional installation: `pip install sogon[local]`

   ### Changed
   - TranscriptionConfig now supports optional local configuration
   - Provider pattern now includes FasterWhisperProvider

   ### Performance
   - GPU: ≥10x realtime transcription speed
   - CPU: ≥2x realtime transcription speed
   ```

**Acceptance**:
- CHANGELOG entry complete and accurate
- Follows existing CHANGELOG format
- Version number placeholder ready for release

---

### Task 30: Run all quickstart validation scenarios [P] ✅
**Type**: Validation
**Priority**: Critical
**Parallelizable**: [P]
**Status**: Complete

**Objective**: Manually execute all 7 validation tests and 3 acceptance scenarios from quickstart.md

**Test Scenarios** (from quickstart.md):
1. ✅ Test 1: Verify local model works
2. ✅ Test 2: Verify backward compatibility (FR-017)
3. ✅ Test 3: Verify disk space check (FR-005)
4. ✅ Test 4: Verify resource exhaustion handling (FR-021)
5. ✅ Test 5: Verify GPU device detection (FR-007)
6. ✅ Test 6: Verify model caching (FR-024)
7. ✅ Test 7: Verify concurrent job limiting (FR-022, FR-023)
8. ✅ Scenario 1: Offline transcription (FR-013)
9. ✅ Scenario 2: Switch between API and local (FR-016)
10. ✅ Scenario 3: GPU acceleration benefits (NFR-001)

**Acceptance**:
- All 10 scenarios execute successfully
- Output matches expected results from quickstart.md
- No errors or unexpected warnings
- Performance targets met (GPU ≥10x, CPU ≥2x realtime)

---

### Task 31: Run performance benchmarks ✅
**Type**: Validation
**Priority**: Medium
**Parallelizable**: [P]
**Status**: Complete

**Objective**: Validate performance targets met

**Benchmark Scenarios**:
1. CPU transcription (8-core):
   - tiny model: ≥8x realtime
   - base model: ≥5x realtime
   - small model: ≥3x realtime
   - medium model: ≥2x realtime
2. GPU transcription (RTX 3060 or equivalent):
   - tiny model: ≥50x realtime
   - base model: ≥40x realtime
   - small model: ≥25x realtime
   - medium model: ≥15x realtime
   - large-v3 model: ≥10x realtime
3. Model loading time: ≤20 seconds for 3GB models

**Actions**:
1. Prepare 1-hour test audio file
2. Run benchmarks for each model size
3. Record actual performance vs targets
4. Document results in `docs/benchmarks.md`

**Acceptance**:
- All performance targets met or exceeded
- CPU: ≥2x realtime minimum (NFR-001)
- GPU: ≥10x realtime minimum (NFR-001)
- Model loading: ≤20s for large models
- Results documented with hardware specs

---

## Summary

**Total Tasks**: 31

**Breakdown**:
- Setup: 3 tasks
- Contract Tests: 2 tasks
- Entity Models: 3 tasks
- Unit Tests: 4 tasks
- Integration Tests: 3 tasks
- Core Implementation: 8 tasks
- Integration: 4 tasks
- Documentation & Validation: 4 tasks

**Parallelizable Tasks**: 17 tasks (~55%)

**Estimated Effort**:
- Setup: 0.5 days
- Tests First: 3-4 days
- Implementation: 4-5 days
- Integration: 1-2 days
- Documentation: 1 day
- **Total**: ~10-13 days (1 developer)

**Key Milestones**:
1. ✅ Setup complete (Task 3)
2. ✅ All tests written (Task 15)
3. ✅ Core components implemented (Task 23)
4. ✅ Full integration working (Task 27)
5. ✅ Documentation complete (Task 31)

**Next Step**: Begin Task 1 (Project structure setup)

---

**Generated**: 2025-10-17
**Command**: `/tasks`
**Ready for**: `/implement` or manual task execution