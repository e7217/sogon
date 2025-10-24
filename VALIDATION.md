# Local Model Implementation Validation Checklist

This document provides a comprehensive checklist for validating the local Whisper model implementation.

## Pre-Validation Setup

### Environment Preparation
- [ ] Python 3.12+ installed
- [ ] sogon package installed with local support: `pipx install sogon[local]` or `uv sync --extra local`
- [ ] Test audio files available (various durations: 5s, 30s, 3min, 10min)
- [ ] CUDA toolkit installed (for GPU testing, optional)

### Verification Commands
```bash
# Check installation
sogon --version

# Verify faster-whisper availability
python -c "import faster_whisper; print('faster-whisper OK')"

# Check CUDA (GPU testing)
nvidia-smi  # Should show GPU info if available
```

## Functional Validation Scenarios

### Scenario 1: Basic Local Model Usage
**Objective**: Verify basic local model transcription works

**Steps**:
1. Run basic transcription with local model:
   ```bash
   sogon run test_audio.mp3 --local-model base
   ```

**Expected Results**:
- [x] Model downloads automatically on first use
- [x] Download progress displayed with percentage
- [x] Model cached for subsequent uses
- [x] Transcription completes successfully
- [x] Output files generated in result/ directory
- [x] Timestamps accurate to ±100ms

**Validation**:
```bash
# Verify model downloaded
ls ~/.cache/sogon/models/  # Should contain base model

# Check output files
ls result/*/  # Should contain transcription files

# Verify no API errors (local mode shouldn't need API key)
# Should work without GROQ_API_KEY or OPENAI_API_KEY set
```

### Scenario 2: Model Size Variations
**Objective**: Verify all model sizes work correctly

**Steps**:
1. Test each model size:
   ```bash
   sogon run test_audio.mp3 --local-model tiny
   sogon run test_audio.mp3 --local-model base
   sogon run test_audio.mp3 --local-model small
   sogon run test_audio.mp3 --local-model medium
   # sogon run test_audio.mp3 --local-model large    # Requires 8GB+ RAM
   # sogon run test_audio.mp3 --local-model large-v2  # Requires 8GB+ RAM
   # sogon run test_audio.mp3 --local-model large-v3  # Requires 8GB+ RAM
   ```

**Expected Results**:
- [x] Each model downloads once and is cached
- [x] Larger models provide better accuracy
- [x] Disk space validated before download
- [x] RAM requirements met or graceful error

**Validation Criteria**:
- Model accuracy improves: tiny < base < small < medium < large
- Cache size stays within limits (SOGON_LOCAL_CACHE_MAX_SIZE_GB)

### Scenario 3: Device Selection
**Objective**: Verify CPU, CUDA, and MPS device support

**Steps**:
1. CPU inference (default):
   ```bash
   sogon run test_audio.mp3 --local-model base --local-device cpu
   ```

2. GPU inference (if available):
   ```bash
   sogon run test_audio.mp3 --local-model base --local-device cuda
   ```

3. Apple Silicon (if available):
   ```bash
   sogon run test_audio.mp3 --local-model base --local-device mps
   ```

**Expected Results**:
- [x] CPU inference works on all systems
- [x] CUDA device detected if available, falls back to CPU if not
- [x] MPS device detected on Apple Silicon
- [x] Auto-detection suggests optimal device
- [x] Graceful error message if device unavailable

**Validation**:
```bash
# Verify device usage
# Should see "Using device: cpu|cuda|mps" in logs

# Check performance difference
# GPU should be 5-10x faster than CPU
```

### Scenario 4: Compute Type/Precision
**Objective**: Verify different precision modes work correctly

**Steps**:
1. Test precision modes:
   ```bash
   sogon run test_audio.mp3 --local-model base --local-compute-type int8
   sogon run test_audio.mp3 --local-model base --local-compute-type int16
   sogon run test_audio.mp3 --local-model base --local-compute-type float16  # GPU
   sogon run test_audio.mp3 --local-model base --local-compute-type float32
   ```

**Expected Results**:
- [x] int8 fastest, lowest accuracy
- [x] float32 slowest, highest accuracy
- [x] float16 requires GPU (CUDA/MPS)
- [x] Memory usage varies: int8 < int16 < float16 < float32

**Validation**:
- Check memory usage during inference
- Verify accuracy/speed tradeoff

### Scenario 5: Advanced Inference Parameters
**Objective**: Verify beam size, temperature, and VAD filter work

**Steps**:
1. Beam size variation:
   ```bash
   sogon run test_audio.mp3 --local-model base --local-beam-size 1   # Fastest
   sogon run test_audio.mp3 --local-model base --local-beam-size 5   # Default
   sogon run test_audio.mp3 --local-model base --local-beam-size 10  # Best quality
   ```

2. Temperature adjustment:
   ```bash
   sogon run test_audio.mp3 --local-model base --local-temperature 0.0  # Deterministic
   sogon run test_audio.mp3 --local-model base --local-temperature 0.5  # More creative
   ```

3. VAD filter:
   ```bash
   sogon run test_audio.mp3 --local-model base --local-vad-filter
   ```

**Expected Results**:
- [x] Higher beam size improves accuracy but slower
- [x] Temperature affects output diversity
- [x] VAD filter removes silence, improves segment boundaries

### Scenario 6: Concurrent Processing
**Objective**: Verify concurrent job handling works correctly

**Steps**:
1. Test concurrent workers:
   ```bash
   sogon run large_audio.mp3 --local-model base --local-max-workers 1  # Sequential
   sogon run large_audio.mp3 --local-model base --local-max-workers 2  # Default
   sogon run large_audio.mp3 --local-model base --local-max-workers 4  # Parallel
   ```

**Expected Results**:
- [x] Higher worker count reduces total time
- [x] Memory usage increases with workers
- [x] Semaphore limits concurrent operations
- [x] No more than max_workers tasks run simultaneously

**Validation**:
- Monitor system resources during processing
- Verify processing time decreases with more workers (up to CPU core count)

### Scenario 7: Environment Variable Configuration
**Objective**: Verify environment variables work correctly

**Steps**:
1. Set environment variables:
   ```bash
   export SOGON_PROVIDER=faster-whisper
   export SOGON_LOCAL_MODEL_NAME=medium
   export SOGON_LOCAL_DEVICE=cpu
   export SOGON_LOCAL_COMPUTE_TYPE=int8
   export SOGON_LOCAL_BEAM_SIZE=7
   export SOGON_LOCAL_TEMPERATURE=0.2
   export SOGON_LOCAL_VAD_FILTER=true
   export SOGON_LOCAL_MAX_WORKERS=3
   ```

2. Run without CLI flags:
   ```bash
   sogon run test_audio.mp3
   ```

**Expected Results**:
- [x] Uses environment variable configuration
- [x] CLI flags override env vars when provided
- [x] Provider auto-set to faster-whisper

**Validation**:
```bash
# Verify config used
# Should see "Using provider: faster-whisper" in logs
# Should use medium model, not base
```

### Scenario 8: Backward Compatibility
**Objective**: Verify existing workflows unchanged

**Steps**:
1. Test legacy API providers still work:
   ```bash
   export GROQ_API_KEY=your_key
   sogon run test_audio.mp3  # Should use Groq (default)

   sogon run test_audio.mp3 --provider openai  # Should use OpenAI
   sogon run test_audio.mp3 --provider groq    # Should use Groq
   ```

**Expected Results**:
- [x] OpenAI provider works as before
- [x] Groq provider works as before
- [x] No breaking changes to existing commands
- [x] API-based providers don't require local model dependencies

**Validation**:
- Run existing scripts/workflows
- Verify output format unchanged
- Check no new required dependencies for API usage

### Scenario 9: Error Handling
**Objective**: Verify graceful error handling and helpful messages

**Steps**:
1. Test error scenarios:
   ```bash
   # Missing faster-whisper
   sogon run test_audio.mp3 --local-model base  # Without sogon[local] installed

   # Insufficient disk space (mock scenario)
   # Set SOGON_LOCAL_DOWNLOAD_ROOT to small partition

   # Insufficient RAM (use large model on low-RAM system)
   sogon run test_audio.mp3 --local-model large-v3  # On 4GB RAM system

   # Unavailable device
   sogon run test_audio.mp3 --local-model base --local-device cuda  # Without GPU
   ```

**Expected Results**:
- [x] Clear error message: "faster-whisper not installed"
- [x] Helpful suggestion: "Install with: pip install sogon[local]"
- [x] Disk space validation before download
- [x] RAM validation before model loading
- [x] Graceful fallback suggestion (try smaller model or CPU)
- [x] Device availability check with fallback suggestion

**Validation**:
- Error messages actionable and user-friendly
- No stack traces for expected errors
- Suggestions lead to successful resolution

### Scenario 10: Auto-Provider Switching
**Objective**: Verify --local-model flag auto-sets provider

**Steps**:
1. Test auto-switching:
   ```bash
   # Should automatically use faster-whisper provider
   sogon run test_audio.mp3 --local-model base
   ```

2. Verify in logs:
   ```bash
   # Should see: "Using provider: faster-whisper"
   # Not: "Using provider: groq" or "Using provider: openai"
   ```

**Expected Results**:
- [x] Using --local-model automatically sets provider to faster-whisper
- [x] No need to specify --provider flag separately
- [x] Intuitive user experience

## Performance Validation

### Scenario 11: Performance Benchmarks
**Objective**: Verify performance meets expectations

**Test Setup**:
- Audio file: 5-minute podcast
- System: 8-core CPU, 16GB RAM, NVIDIA GPU (if available)

**Benchmark Tests**:

1. **CPU Performance**:
   ```bash
   time sogon run 5min_audio.mp3 --local-model base --local-device cpu --local-compute-type int8
   ```
   - [ ] Expected: ~30-60 seconds (0.1-0.2x realtime)

2. **GPU Performance**:
   ```bash
   time sogon run 5min_audio.mp3 --local-model base --local-device cuda --local-compute-type float16
   ```
   - [ ] Expected: ~5-15 seconds (0.02-0.05x realtime, 5-10x faster than CPU)

3. **Model Size Performance**:
   ```bash
   time sogon run 5min_audio.mp3 --local-model tiny --local-device cpu
   time sogon run 5min_audio.mp3 --local-model base --local-device cpu
   time sogon run 5min_audio.mp3 --local-model medium --local-device cpu
   ```
   - [ ] Expected: tiny < base < medium (2-3x difference between sizes)

4. **Concurrent Processing Performance**:
   ```bash
   time sogon run 10min_audio.mp3 --local-model base --local-max-workers 1
   time sogon run 10min_audio.mp3 --local-model base --local-max-workers 4
   ```
   - [ ] Expected: 4 workers should be 2-3x faster (with diminishing returns)

**Resource Usage Validation**:
- [ ] Peak RAM usage: tiny (~500MB), base (~1GB), medium (~3GB), large (~8GB)
- [ ] Disk usage: Cached models within configured limits
- [ ] No memory leaks during extended usage

## Integration Validation

### Scenario 12: Integration Test Execution
**Objective**: Verify all integration tests pass

**Steps**:
1. Run integration test suite:
   ```bash
   pytest tests/integration/providers/ -v
   ```

2. Check specific test categories:
   ```bash
   pytest tests/integration/providers/test_local_transcription_e2e.py -v
   pytest tests/integration/providers/test_gpu_and_concurrency.py -v
   pytest tests/integration/providers/test_backward_compatibility.py -v
   ```

**Expected Results**:
- [ ] All integration tests pass
- [ ] No skip markers remaining
- [ ] Test coverage ≥80% for local provider components

**Validation**:
```bash
# Check coverage
pytest tests/integration/providers/ --cov=sogon.providers.local --cov-report=term-missing
```

## User Acceptance Testing

### Scenario 13: Real-World Use Cases
**Objective**: Validate with real user workflows

**Test Cases**:

1. **Podcast Transcription**:
   ```bash
   sogon run podcast_episode.mp3 --local-model medium --local-vad-filter
   ```
   - [ ] Accurate speaker transcription
   - [ ] Proper silence handling with VAD
   - [ ] Reasonable processing time

2. **YouTube Video**:
   ```bash
   sogon run "https://youtube.com/watch?v=..." --local-model base
   ```
   - [ ] Audio extraction works
   - [ ] Local transcription accurate
   - [ ] Output format correct

3. **Multi-Language Content**:
   ```bash
   sogon run korean_audio.mp3 --local-model base
   sogon run english_audio.mp3 --local-model base
   ```
   - [ ] Auto language detection works
   - [ ] Transcription quality acceptable for both languages

4. **Large File Processing**:
   ```bash
   sogon run 2hour_lecture.mp3 --local-model base --local-max-workers 4
   ```
   - [ ] File chunking works correctly
   - [ ] Concurrent processing efficient
   - [ ] Segment timestamps accurate across chunks

## Validation Completion Checklist

### Core Functionality
- [ ] All 7 model sizes download and run correctly
- [ ] CPU/CUDA/MPS device selection works
- [ ] All compute types (int8/int16/float16/float32) function properly
- [ ] Beam size, temperature, VAD filter parameters validated
- [ ] Concurrent processing with worker control verified

### Configuration
- [ ] All 10 environment variables work correctly
- [ ] All 7 CLI flags function as expected
- [ ] Priority order correct: CLI > env vars > defaults
- [ ] Auto-provider switching functional

### Integration
- [ ] Provider pattern integration complete
- [ ] Backward compatibility with OpenAI/Groq maintained
- [ ] ServiceContainer properly wired
- [ ] TranscriptionService supports both legacy and provider flows

### Quality
- [ ] All integration tests pass
- [ ] Error messages helpful and actionable
- [ ] Resource validation prevents issues
- [ ] Documentation accurate and complete

### Performance
- [ ] CPU performance within expected range
- [ ] GPU acceleration provides 5-10x speedup
- [ ] Model size/quality tradeoff validated
- [ ] Concurrent processing improves throughput

## Sign-Off

**Validation Completed By**: _____________
**Date**: _____________
**Environment**: _____________
**sogon Version**: _____________
**faster-whisper Version**: _____________

**Overall Status**: [ ] PASS / [ ] FAIL

**Notes**:
