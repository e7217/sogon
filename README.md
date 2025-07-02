# SOGON

An AI-powered automation tool that extracts audio from video URLs or media files and generates subtitles using advanced speech recognition technology.

> **[한국어](README_ko.md)**

## Key Features

- **Flexible Audio Extraction**: High-quality audio extraction from video URLs or local media files
- **AI Speech Recognition**: Accurate Korean speech recognition with advanced AI models
- **Large File Processing**: Automatic workaround for 24MB limit (file splitting)
- **Precise Timestamps**: Segment-level time information in HH:mm:ss.SSS format
- **Intelligent Text Correction**: Dual correction system (pattern-based + AI-based)
- **Systematic Output**: Separate storage of original/corrected versions

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

## Quick Start

### 1. API Key Setup

Create a `.env` file and set your Groq API key:

```bash
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional: for AI text correction
```

### 2. Basic Usage

```bash
# Process video URL
sogon run "https://www.youtube.com/watch?v=VIDEO_ID"

# Process local media file
sogon run "/path/to/video/file.mp4"
```

## System Architecture

```
Video URL/File → Audio Extract → Speech Recognition → Text Correction → File Save
      ↓             ↓                ↓                 ↓              ↓
  Downloader    Audio Tool    AI Speech Model     AI Correction   result/
```

## Processing Steps

1. **Audio Extraction**: Extract audio from video URLs or local files using media processing tools
2. **File Processing**: Split large files to comply with API limitations
3. **Speech Recognition**: Process audio with advanced AI models for Korean text
4. **Text Correction**: Apply pattern-based and AI-based corrections
5. **Output Generation**: Save original and corrected versions with timestamps

## Output File Structure

**Organized by Date/Time/Title:**
```
result/
└── yyyyMMDD_HHmmss_video_title/         # Timestamped folder for each video
    ├── video_title.txt                  # Original continuous text
    ├── video_title_metadata.json        # Original metadata
    ├── video_title_timestamps.txt       # Original timestamps
    ├── video_title_corrected.txt        # Corrected text
    ├── video_title_corrected_metadata.json # Corrected metadata
    └── video_title_corrected_timestamps.txt # Corrected timestamps
```

### Timestamp File Format
```
Subtitle with Timestamps (Corrected)
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
| **AI Correction** | Large Language Model | Text correction |
| **Environment Management** | Configuration Manager | API key management |

## Output Files

The tool generates organized output files with timestamps and metadata for both original and corrected versions.

## Advanced Features

### Existing File Correction
The tool provides functionality to correct existing transcript files with AI-based improvements.

### CLI Options

| Option | Description | Default |
|--------|-------------|----------|
| `--format`, `-f` | Output subtitle format (txt, srt, vtt, json) | txt |
| `--output-dir`, `-o` | Custom output directory | ./result |
| `--no-correction` | Disable text correction | False |
| `--no-ai-correction` | Disable AI-based text correction | False |
| `--keep-audio` | Keep downloaded audio files | False |
| `--translate` | Enable subtitle translation | False |
| `--target-language`, `-t` | Target language for translation | None |
| `--source-language`, `-s` | Source language for Whisper | auto-detect |
| `--log-level` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |

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

# Disable text correction
sogon run "video.mp4" --no-correction

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


## Requirements

### System Requirements
- Python 3.12+
- Audio processing tools
- Internet connection (for video URL download and AI API access)

### Dependencies
The project requires various Python packages for audio processing, AI integration, and configuration management. See the project configuration file for specific requirements.

## Troubleshooting

- **Audio Tools**: Install required audio processing tools via package manager
- **API Key**: Set up valid AI service API key in `.env` file
- **Network Issues**: Ensure stable internet connection

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
