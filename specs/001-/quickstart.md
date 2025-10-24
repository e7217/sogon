# Quickstart: Local Whisper Model Support

**Feature**: Local Whisper model inference
**Target Users**: Developers implementing and testing the feature
**Prerequisites**: sogon installed with local model dependencies

---

## Installation

### Option 1: Full Installation (API + Local)

```bash
# Install sogon with local model support
pip install sogon[local]

# Or with uv (recommended)
uv pip install sogon[local]
```

### Option 2: API-Only Installation (Backward Compatible)

```bash
# Existing users - no changes needed
pip install sogon

# Local model support NOT available
```

---

## Quick Start: Local Transcription

### 1. Basic Usage (CPU, Base Model)

```bash
# Transcribe with local model using defaults
sogon transcribe audio.mp3 --provider faster-whisper

# First run: Model auto-downloads from Hugging Face
# Output: Transcription completes offline
```

**Expected Output**:
```
[2025-10-17 10:30:00] INFO: Using local model: base (CPU)
[2025-10-17 10:30:01] INFO: Downloading model from Hugging Face...
[2025-10-17 10:30:15] INFO: Model cached at ~/.cache/sogon/models/faster-whisper-base
[2025-10-17 10:30:15] INFO: Model loaded (142MB)
[2025-10-17 10:30:15] INFO: Transcribing audio.mp3 (3m 45s)...
[2025-10-17 10:32:00] INFO: Transcription complete (2.5x realtime)

Transcription saved to: audio.srt
```

---

### 2. GPU Acceleration (CUDA)

```bash
# Use CUDA GPU with float16 precision
sogon transcribe audio.mp3 \
  --provider faster-whisper \
  --device cuda \
  --compute-type float16 \
  --local-model medium

# Expected: 10-15x realtime speed
```

**Validation**:
- Check GPU usage: `nvidia-smi` shows sogon process
- Verify speed: 1hr audio transcribes in ~4-6 minutes
- Confirm VRAM: Model loaded into GPU memory

---

### 3. Environment Variable Configuration

```bash
# Set defaults via environment variables
export SOGON_PROVIDER=faster-whisper
export SOGON_LOCAL_MODEL_NAME=small
export SOGON_LOCAL_DEVICE=cuda
export SOGON_LOCAL_COMPUTE_TYPE=float16
export SOGON_LOCAL_MAX_WORKERS=4

# Now simple command uses local model
sogon transcribe audio.mp3
```

---

### 4. Concurrent Transcriptions

```bash
# Process multiple files concurrently
sogon transcribe audio1.mp3 audio2.mp3 audio3.mp3 \
  --provider faster-whisper \
  --device cuda \
  --max-workers 2

# Default: 2 concurrent jobs (FR-022)
# Override with --max-workers flag
```

---

## Validation Tests

### Test 1: Verify Local Model Works

```bash
# 1. Transcribe with local model
sogon transcribe test_audio.mp3 --provider faster-whisper --output local.srt

# 2. Transcribe with API (for comparison)
sogon transcribe test_audio.mp3 --provider openai --output api.srt

# 3. Compare outputs - formats should match (FR-011)
diff local.srt api.srt
# Expected: Different text (models differ) but identical SRT format
```

---

### Test 2: Verify Backward Compatibility (FR-017)

```bash
# Existing API-based workflow must work unchanged
sogon transcribe audio.mp3  # Uses OpenAI by default

# No errors, no warnings, identical behavior
```

---

### Test 3: Verify Disk Space Check (FR-005)

```bash
# Fill disk to <500MB free
# Try to download large model
sogon transcribe audio.mp3 --provider faster-whisper --local-model large

# Expected error:
# Error: Insufficient disk space for model 'large'
# Required: 2.9 GB
# Available: 0.4 GB
# Please free up at least 2.5 GB of disk space
```

---

### Test 4: Verify Resource Exhaustion Handling (FR-021)

```python
# Simulate memory exhaustion during transcription
import psutil

# Monitor memory usage
process = psutil.Process()

# Start transcription
# sogon transcribe large_audio.mp3 --provider faster-whisper --local-model large

# Expected: Clear error when RAM > 90%
# Error: Insufficient memory for transcription
# Current usage: 28GB / 32GB (87%)
# Minimum required: 8GB for model 'large'
# Please close other applications or use smaller model
```

---

### Test 5: Verify GPU Device Detection (FR-007)

```bash
# Request GPU on CPU-only machine
sogon transcribe audio.mp3 --provider faster-whisper --device cuda

# Expected error (FR-009):
# Error: Device 'cuda' not available
# CUDA not detected on this system
# Available devices: cpu
# Install CUDA 11.8+ or use --device cpu
```

---

### Test 6: Verify Model Caching (FR-024)

```bash
# First transcription: downloads model
time sogon transcribe audio1.mp3 --provider faster-whisper --local-model base
# Output: ~20 seconds (includes download)

# Second transcription: uses cached model
time sogon transcribe audio2.mp3 --provider faster-whisper --local-model base
# Output: ~2 seconds (no download, model loaded from cache)
```

---

### Test 7: Verify Concurrent Job Limiting (FR-022, FR-023)

```bash
# Start 3 transcriptions simultaneously
sogon transcribe audio1.mp3 --provider faster-whisper &
sogon transcribe audio2.mp3 --provider faster-whisper &
sogon transcribe audio3.mp3 --provider faster-whisper &

# Expected: Only 2 run concurrently (default max_workers=2)
# Third waits for first two to complete

# Check with:
ps aux | grep sogon
# Should show max 2 active transcription processes
```

---

## User Acceptance Scenarios

### Scenario 1: Offline Transcription (FR-013)

**Given**: User has pre-downloaded model
**When**: User disconnects from internet and transcribes
**Then**: Transcription succeeds without network access

```bash
# Pre-download model
sogon transcribe dummy.mp3 --provider faster-whisper --local-model base

# Disconnect network
sudo ip link set eth0 down

# Transcribe offline
sogon transcribe audio.mp3 --provider faster-whisper --local-model base
# Expected: Success (no network needed)
```

---

### Scenario 2: Switch Between API and Local (FR-016)

**Given**: User has existing API-based workflow
**When**: User switches to local provider
**Then**: No code changes required, just config change

```bash
# API transcription
sogon transcribe audio.mp3

# Switch to local (via env var)
export SOGON_PROVIDER=faster-whisper
sogon transcribe audio.mp3

# Or via CLI flag
sogon transcribe audio.mp3 --provider faster-whisper
```

---

### Scenario 3: GPU Acceleration Benefits (Acceptance Scenario 2)

**Given**: User has CUDA-capable GPU
**When**: User configures GPU acceleration
**Then**: Transcription significantly faster than CPU

```bash
# CPU transcription
time sogon transcribe audio.mp3 --provider faster-whisper --device cpu
# Output: 1hr audio → ~30min (2x realtime)

# GPU transcription
time sogon transcribe audio.mp3 --provider faster-whisper --device cuda
# Output: 1hr audio → ~4min (15x realtime)

# Verify: GPU transcription ≥ 2x faster than CPU (NFR-001)
```

---

## Troubleshooting

### Issue: "faster-whisper not found"

**Cause**: Local model dependencies not installed
**Solution**: Install with local extras

```bash
pip install sogon[local]
# Or: uv pip install sogon[local]
```

---

### Issue: "CUDA not available"

**Cause**: CUDA not installed or GPU drivers missing
**Solution**: Install CUDA 11.8+ and compatible drivers

```bash
# Check CUDA version
nvidia-smi

# If missing, install CUDA:
# https://developer.nvidia.com/cuda-downloads

# Verify PyTorch sees CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

---

### Issue: "Insufficient disk space"

**Cause**: Not enough storage for model download
**Solution**: Free disk space or use smaller model

```bash
# Check available space
df -h ~/.cache/sogon/models

# Use smaller model
sogon transcribe audio.mp3 --provider faster-whisper --local-model tiny
# tiny model: only 75MB
```

---

### Issue: "Memory exhausted during transcription"

**Cause**: Model too large for available RAM/VRAM
**Solution**: Use smaller model or close other applications

```bash
# Check memory usage
free -h

# Use smaller model
sogon transcribe audio.mp3 --provider faster-whisper --local-model small

# Or process in batches with single worker
sogon transcribe audio.mp3 --provider faster-whisper --max-workers 1
```

---

## Performance Benchmarks

| Model | Size | CPU (8-core) | GPU (RTX 3060) | Memory | VRAM |
|-------|------|--------------|----------------|--------|------|
| tiny | 75MB | 8x realtime | 50x realtime | 1GB | 1GB |
| base | 142MB | 5x realtime | 40x realtime | 1.5GB | 1.5GB |
| small | 466MB | 3x realtime | 25x realtime | 2GB | 2GB |
| medium | 1.5GB | 2x realtime | 15x realtime | 4GB | 4GB |
| large-v3 | 2.9GB | 1x realtime | 10x realtime | 8GB | 8GB |

**Note**: Benchmarks based on faster-whisper documentation. Actual performance varies by hardware.

---

## Next Steps

After validating quickstart scenarios:

1. Run unit tests: `pytest tests/unit/`
2. Run contract tests: `pytest tests/contract/`
3. Run integration tests: `pytest tests/integration/`
4. Verify all 7 acceptance scenarios pass
5. Verify 6 edge cases handled correctly

---

## Documentation References

- [Feature Specification](./spec.md) - Full requirements
- [Data Model](./data-model.md) - Entity definitions
- [Research](./research.md) - Technical decisions
- [Implementation Plan](./plan.md) - Development roadmap

---

**Quickstart Complete** - Ready for implementation following TDD workflow.
