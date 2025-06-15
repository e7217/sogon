# 🎥 Video Subtitle Generator (Groq Whisper Turbo)

An AI-powered automation tool that extracts audio from video URLs or media files and generates subtitles using Groq Whisper Turbo.

> **[한국어](README_ko.md)** 📖

## ✨ Key Features

- 🎬 **Flexible Audio Extraction**: High-quality audio extraction from video URLs or local media files via yt-dlp
- 🤖 **AI Speech Recognition**: Accurate Korean speech recognition with Groq Whisper Turbo
- 📏 **Large File Processing**: Automatic workaround for 24MB limit (file splitting)
- ⏰ **Precise Timestamps**: Segment-level time information in HH:mm:ss.SSS format
- 🧠 **Intelligent Text Correction**: Dual correction system (pattern-based + AI-based)
- 📁 **Systematic Output**: Separate storage of original/corrected versions

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Install dependencies
uv sync

# Or using pip
pip install groq python-dotenv yt-dlp pydub
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

## 📋 System Architecture

```
Video URL/File → Audio Extract → Speech Recognition → Text Correction → File Save
      ↓             ↓                ↓                 ↓              ↓
    yt-dlp      ffmpeg        Groq Whisper         AI Correction   result/
```

## 🔄 Processing Steps

### Step 1: Audio Extraction
- **Tools**: `yt-dlp` + `ffmpeg`
- **Input**: Video URLs (YouTube, etc.) or local media files
- **Format**: WAV (high-quality audio)
- **Location**: Temporary directory

### Step 2: File Size Optimization
- **Limitation**: Groq API 24MB limit
- **Method**: Time-based automatic splitting
- **Tool**: `pydub`

### Step 3: AI Speech Recognition
- **API**: Groq Whisper Turbo (`whisper-large-v3-turbo`)
- **Language**: Korean optimization
- **Output**: Text + timestamps + confidence metadata

### Step 4: Text Correction
#### 4-1. Pattern-based Correction
```python
# Automatic correction of common speech recognition error patterns
'PAST API' → 'FastAPI'
'보커' → '도커'
'제미나이' → 'Gemini'
```

#### 4-2. AI-based Correction
- **Model**: `llama-3.3-70b-versatile`
- **Function**: Context-aware intelligent correction
- **Processing**: Technical terms, grammar, semantic consistency correction

#### 4-3. Timestamp Alignment
- Automatic chronological sorting
- Overlapping segment correction
- HH:mm:ss.SSS format standardization

## 📁 Output File Structure

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

## ⚙️ Tech Stack

|  Component | Tool/Library | Role |
|-----------|--------------|------|
| **Audio Extraction** | `yt-dlp` + `ffmpeg` | Video URL/File → WAV conversion |
| **Audio Processing** | `pydub` | File splitting, format conversion |
| **Speech Recognition** | `Groq Whisper Turbo` | Speech → Text + metadata |
| **AI Correction** | `Groq LLM (llama-3.3-70b)` | Text correction |
| **Environment Management** | `python-dotenv` | API key management |

## 📊 Metadata Structure

```json
{
  "chunk_number": 1,
  "total_chunks": 3,
  "language": "Korean",
  "duration": 117.96,
  "segments": [
    {
      "start": 0.0,
      "end": 6.0,
      "text": "Hello. Actually, I was going to continue the visual story writing series,",
      "tokens": [50365, 38962, 9820, 13, ...],
      "avg_logprob": -0.4902137,
      "compression_ratio": 0.6944444,
      "no_speech_prob": 1.5166007e-10
    }
  ]
}
```

## 🛠️ Advanced Features

### Existing File Correction
```python
from main import correct_existing_transcript_file

# Correct existing timestamp file
corrected_file = correct_existing_transcript_file(
    './result/video_title_timestamps.txt',
    use_ai_correction=True
)
```

### Configuration Options
```python
# Control correction features
youtube_to_subtitle(
    url,
    output_dir="./result",
    subtitle_format="txt",
    enable_correction=True,      # Enable text correction
    use_ai_correction=True       # Enable AI-based correction
)
```

## 🔧 Error Handling

### Automatic File Size Limit Processing
```python
# Automatic splitting when exceeding 24MB
if file_size_mb > 24:
    chunks = split_audio_by_size(audio_path, max_size_mb=24)
    # Process each chunk individually and combine
```

### API Error Recovery
- Save partial results on Groq API call failure
- Retry logic for network errors
- Automatic temporary file cleanup

## 💡 Usage Examples

### Basic Usage
```bash
# Process video URL
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Process local media file
python main.py "/path/to/video.mp4"
```

### Command Line Options
```bash
# Use test URL when running without URL
python main.py

# Set API key via environment variable
export GROQ_API_KEY=your_api_key_here
python main.py "video_url_or_file_path"
```

## 📋 Requirements

### System Requirements
- Python 3.12+
- ffmpeg (for audio processing)
- Internet connection (for video URL download and Groq API)

### Python Packages
```toml
[project]
dependencies = [
    "groq>=0.26.0",
    "python-dotenv>=1.0.0",
    "yt-dlp>=2024.3.10",
    "pydub>=0.25.1",
]
```

## 🐛 Troubleshooting

### ffmpeg Installation
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### API Key Errors
- Check valid API key in Groq console
- Verify `.env` file path and format
- Check API usage limits

### Speech Recognition Errors
- Check internet connection status
- Verify audio file quality (exclude corrupted files)
- Check Groq API service status

## 📈 Performance Optimization

### Speed Improvement
- Chunk-based parallel processing
- Memory-efficient streaming
- Automatic temporary file cleanup

### Quality Enhancement
- High-quality audio extraction (192kbps WAV)
- Dual correction system (pattern + AI)
- Confidence-based result validation

## 📄 License

This project is distributed under the MIT License.

## 🤝 Contributing

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support

If you encounter any issues or have questions, please contact us through GitHub Issues.

---

**⚡ Experience fast and accurate video subtitle generation\!**
