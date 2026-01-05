# SOGON

An AI-powered automation tool that extracts audio from video URLs or media files and generates subtitles using advanced speech recognition technology.

> **[한국어](README_ko.md)**

## Key Features

- **Flexible Audio Extraction**: High-quality audio extraction from video URLs or local media files
- **AI Speech Recognition**: Accurate Korean speech recognition with advanced AI models
- **Local & Cloud Inference**: Choose between local Whisper models or cloud APIs (OpenAI, Groq)
- **Large File Processing**: Automatic workaround for 24MB limit (file splitting)
- **Precise Timestamps**: Segment-level time information in HH:mm:ss.SSS format
- **Systematic Output**: Organized result storage with metadata

## Installation

### Method 1: Install with pipx (Recommended)

```bash
# Install globally with pipx
pipx install sogon

# Use the CLI tool
sogon run "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Package Management

```bash
# Upgrade to latest version
pipx upgrade sogon

# Check installed version
pipx list

# Uninstall
pipx uninstall sogon

# Reinstall (if needed)
pipx reinstall sogon
```

### Method 2: Development Setup

```bash
# Clone and install dependencies
git clone <repository-url>
cd sogon
uv sync
```

### Method 3: Install with Local Model Support

For offline transcription without API dependencies:

```bash
# Install with local model support
pipx install sogon[local]

# Or for development
uv sync --extra local
```

This installs `stable-ts` (stable-whisper) for local Whisper model inference with improved timestamp accuracy for subtitles. Supports CPU/GPU acceleration.

## Quick Start

### 1. API Key Setup

Create a `.env` file and set your Groq API key:

```bash
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional: for translation
```

### 2. Basic Usage

```bash
# Process video URL
sogon run "https://www.youtube.com/watch?v=VIDEO_ID"

# Process local media file
sogon run "/path/to/video/file.mp4"
```

### 3. Local Model Usage (Optional)

Use local Whisper models for offline transcription without API keys:

```bash
# Use local base model (fastest, good accuracy)
sogon run "video.mp4" --local-model base

# Use larger model for better accuracy
sogon run "video.mp4" --local-model medium

# GPU acceleration (if CUDA available)
sogon run "video.mp4" --local-model base --local-device cuda

# Set environment variable for default local usage
export SOGON_PROVIDER=stable-whisper
export SOGON_LOCAL_MODEL_NAME=base
sogon run "video.mp4"
```

Available local models: `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3`

## Configuration

Customize default behavior with persistent settings:

```bash
# View all settings
sogon config get

# Set default output format
sogon config set default_subtitle_format srt

# Set default output directory
sogon config set output_base_dir ~/subtitles

# Enable translation by default
sogon config set enable_translation true

# View detailed options with ranges
sogon config get -v

# Reset to defaults
sogon config reset
```

Configuration is stored in `~/.sogon/config.yaml`.

### Available Settings

| Key | Description | Default |
|-----|-------------|---------|
| `output_base_dir` | Output directory | ./result |
| `default_subtitle_format` | Subtitle format (txt/srt/vtt/json) | txt |
| `transcription_provider` | Provider (groq/openai/stable-whisper) | groq |
| `enable_translation` | Enable translation by default | false |
| `default_translation_language` | Target language | ko |
| `default_source_language` | Source language | auto |
| `log_level` | Logging level | INFO |
| `keep_temp_files` | Keep temporary files | false |
| `max_workers` | Concurrent workers (1-16) | 4 |
| `max_chunk_size_mb` | Audio chunk size (1-100) | 24 |

**Local Model Settings:**

| Key | Description | Default |
|-----|-------------|---------|
| `local_model_name` | Model (tiny~large-v3-turbo) | base |
| `local_device` | Device (cpu/cuda/mps) | cuda |
| `local_compute_type` | Precision (int8~float32) | float16 |
| `local_beam_size` | Beam size (1-10) | 5 |
| `local_temperature` | Temperature (0.0-1.0) | 0.0 |
| `local_vad_filter` | VAD filter | false |

## System Architecture

```
Video URL/File → Audio Extract → Speech Recognition → File Save
      ↓             ↓                ↓                  ↓
  Downloader    Audio Tool    AI Speech Model      result/
```

## Processing Steps

1. **Audio Extraction**: Extract audio from video URLs or local files using media processing tools
2. **File Processing**: Split large files to comply with API limitations
3. **Speech Recognition**: Process audio with advanced AI models
4. **Output Generation**: Save transcription results with timestamps

## Output File Structure

**Organized by Date/Time/Title:**
```
result/
└── yyyyMMDD_HHmmss_video_title/         # Timestamped folder for each video
    ├── video_title.txt                  # Continuous text
    ├── video_title_metadata.json        # Metadata with segments
    └── video_title_timestamps.txt       # Timestamps with text
```

### Timestamp File Format
```
Subtitle with Timestamps
==================================================

[00:00:00.560 → 00:00:03.520] Hello. Actually, I was going to continue the visual story writing series,
[00:00:03.520 → 00:00:12.839] but there was a problem in the middle,
[00:00:12.839 → 00:00:14.039] I did up to episode 4, filmed episode 5 and need to upload it, but it's not easy.
```

## Tech Stack

|  Component | Function | Role |
|-----------|----------|------|
| **Audio Extraction** | Media Downloader + Audio Processor | Video URL/File → Audio conversion |
| **Audio Processing** | Audio Library | File splitting, format conversion |
| **Speech Recognition** | AI Speech Model | Speech → Text + metadata |
| **Translation** | Large Language Model | Subtitle translation |
| **Environment Management** | Configuration Manager | API key and settings |

## Output Files

The tool generates organized output files with timestamps and metadata.

## CLI Options

| Option | Description | Default |
|--------|-------------|----------|
| `--format`, `-f` | Output subtitle format (txt, srt, vtt, json) | txt |
| `--output-dir`, `-o` | Custom output directory | ./result |
| `--keep-audio` | Keep downloaded audio files | False |
| `--translate` | Enable subtitle translation | False |
| `--target-language`, `-t` | Target language for translation | None |
| `--source-language`, `-s` | Source language for Whisper | auto-detect |
| `--log-level` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| **Local Model Options** | | |
| `--local-model` | Local Whisper model (tiny/base/small/medium/large/large-v2/large-v3) | None |
| `--local-device` | Compute device (cpu/cuda/mps) | cpu |
| `--local-compute-type` | Compute precision (int8/int16/float16/float32) | int8 |
| `--local-beam-size` | Beam size for inference (1-10) | 5 |
| `--local-temperature` | Sampling temperature (0.0-1.0) | 0.0 |
| `--local-vad-filter` | Enable voice activity detection filter | False |
| `--local-max-workers` | Max concurrent workers (1-10) | 2 |

## Error Handling

- Automatic file splitting for large files (>24MB)
- Partial result saving on failures
- Automatic cleanup of temporary files

## CLI Usage Examples

### Basic Usage
```bash
# Process video URL
sogon run "https://www.youtube.com/watch?v=VIDEO_ID"

# Process local media file
sogon run "/path/to/video/file.mp4"
```

### Advanced Options
```bash
# Specify output format
sogon run "video.mp4" --format srt

# Set custom output directory
sogon run "video.mp4" --output-dir ./my-results

# Keep downloaded audio files
sogon run "https://youtube.com/watch?v=..." --keep-audio

# Enable translation to Korean
sogon run "video.mp4" --translate --target-language ko

# Set source language for better transcription
sogon run "video.mp4" --source-language en

# Adjust logging level
sogon run "video.mp4" --log-level DEBUG
```

### Translation Features
```bash
# List supported languages
sogon list-languages

# Translate to different languages
sogon run "video.mp4" --translate --target-language en  # English
sogon run "video.mp4" --translate --target-language ko  # Korean
```

### Output Formats
```bash
# Different subtitle formats
sogon run "video.mp4" --format txt   # Plain text (default)
sogon run "video.mp4" --format srt   # SubRip subtitle format
sogon run "video.mp4" --format vtt   # WebVTT format
sogon run "video.mp4" --format json  # JSON format with metadata
```

### Local Model Examples
```bash
# Basic local transcription (no API key required)
sogon run "video.mp4" --local-model base

# High accuracy with larger model
sogon run "video.mp4" --local-model large-v3

# GPU acceleration for faster processing
sogon run "video.mp4" --local-model base --local-device cuda --local-compute-type float16

# Fine-tuned inference parameters
sogon run "video.mp4" --local-model medium --local-beam-size 10 --local-temperature 0.2

# Enable voice activity detection for better accuracy
sogon run "video.mp4" --local-model base --local-vad-filter

# Concurrent processing for large files
sogon run "video.mp4" --local-model base --local-max-workers 4

# Environment variable configuration
export SOGON_PROVIDER=stable-whisper
export SOGON_LOCAL_MODEL_NAME=medium
export SOGON_LOCAL_DEVICE=cuda
sogon run "video.mp4"
```


## Requirements

### System Requirements
- Python 3.12+
- Audio processing tools
- Internet connection (for video URL download and cloud API access)

### Dependencies
The project requires various Python packages for audio processing, AI integration, and configuration management. See the project configuration file for specific requirements.

### Optional: Local Model Support
- **stable-ts** (stable-whisper) - install with `pipx install sogon[local]`
  - Provides improved timestamp accuracy for subtitle generation
  - Better word-level timing and silence suppression
- **CUDA Toolkit** (for GPU acceleration, optional)
- **Disk space**: 100MB - 3GB depending on model size
- **RAM**: 1GB - 8GB depending on model and device

## Troubleshooting

- **Audio Tools**: Install required audio processing tools via package manager
- **API Key**: Set up valid AI service API key in `.env` file
- **Network Issues**: Ensure stable internet connection
- **Local Model Issues**:
  - Install local dependencies: `pipx install sogon[local]`
  - Check disk space for model downloads (100MB - 3GB)
  - For GPU issues: Verify CUDA installation with `nvidia-smi`
  - Reduce model size if out of memory (try `base` instead of `large`)

## License

This project is distributed under the MIT License.

## Contributing

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

If you encounter any issues or have questions, please contact us through GitHub Issues.
