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

## Quick Start

### 1. Environment Setup

```bash
# Install dependencies
uv sync
```

### 2. API Key Setup

Create a `.env` file and set your Groq API key:

```bash
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Run

```bash
# Process video URL
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Process local media file
python main.py "/path/to/video/file.mp4"
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

### Configuration Options
Various options are available to control correction features, output formats, and processing behavior.

## Error Handling

- Automatic file splitting for large files (>24MB)
- Partial result saving on failures
- Automatic cleanup of temporary files

## Usage Examples

### Basic Usage
```bash
# Process video URL
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Process local media file
python main.py "/path/to/video.mp4"
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
