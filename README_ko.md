# 🎥 YouTube 자막 생성기 (Groq Whisper Turbo)

YouTube 링크에서 음성을 추출하고 Groq Whisper Turbo를 이용해 자막을 생성하는 AI 기반 자동화 도구입니다.

## ✨ 주요 기능

- 🎬 **YouTube 오디오 자동 추출**: yt-dlp를 통한 고품질 오디오 다운로드
- 🤖 **AI 음성인식**: Groq Whisper Turbo로 정확한 한국어 음성인식
- 📏 **대용량 파일 처리**: 24MB 제한 자동 우회 (파일 분할)
- ⏰ **정밀한 타임스탬프**: HH:mm:ss.SSS 형식의 세그먼트별 시간 정보
- 🧠 **지능형 텍스트 보정**: 패턴 기반 + AI 기반 이중 보정
- 📁 **체계적인 출력**: 원본/보정본 분리 저장

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치
uv sync

# 또는 pip 사용시
pip install groq python-dotenv yt-dlp pydub
```

### 2. API 키 설정

`.env` 파일을 생성하고 Groq API 키를 설정하세요:

```bash
GROQ_API_KEY=your_groq_api_key_here
```

### 3. 실행

```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

## 📋 시스템 아키텍처

```
YouTube URL → 오디오 추출 → 음성인식 → 텍스트 보정 → 파일 저장
     ↓           ↓            ↓          ↓          ↓
   yt-dlp    ffmpeg     Groq Whisper   AI보정    result/
```

## 🔄 처리 단계

### 1단계: YouTube 오디오 추출
- **도구**: `yt-dlp` + `ffmpeg`
- **형식**: WAV (고품질 오디오)
- **위치**: 임시 디렉토리

### 2단계: 파일 크기 최적화
- **제한**: Groq API 24MB 제한
- **방식**: 시간 기준 자동 분할
- **도구**: `pydub`

### 3단계: AI 음성인식
- **API**: Groq Whisper Turbo (`whisper-large-v3-turbo`)
- **언어**: 한국어 최적화
- **출력**: 텍스트 + 타임스탬프 + 신뢰도 메타데이터

### 4단계: 텍스트 보정
#### 4-1. 패턴 기반 보정
```python
# 일반적인 음성인식 오류 패턴 자동 수정
'PAST API' → 'FastAPI'
'보커' → '도커'
'제미나이' → 'Gemini'
'솔롬봇' → '솔론봇'
'웅 떠버린' → '비어버린'
```

#### 4-2. AI 기반 보정
- **모델**: `llama-3.3-70b-versatile`
- **기능**: 문맥 이해 기반 지능형 교정
- **처리**: 기술 용어, 문법, 의미 일관성 수정

#### 4-3. 타임스탬프 정렬
- 시간순 자동 정렬
- 겹치는 구간 수정
- HH:mm:ss.SSS 형식 통일

## 📁 출력 파일 구조

**날짜/시간/제목별 정리:**
```
result/
└── yyyyMMDD_HHmmss_비디오제목/          # 각 비디오별 타임스탬프 폴더
    ├── 비디오제목.txt                  # 원본 연속 텍스트
    ├── 비디오제목_metadata.json        # 원본 메타데이터
    ├── 비디오제목_timestamps.txt       # 원본 타임스탬프
    ├── 비디오제목_corrected.txt        # 보정된 텍스트
    ├── 비디오제목_corrected_metadata.json # 보정된 메타데이터
    └── 비디오제목_corrected_timestamps.txt # 보정된 타임스탬프
```

**예시:**
```
result/
└── 20250606_153406_인공지능 카톡봇 - 솔론봇(1) 소개 및 구조 설명/
    ├── 인공지능 카톡봇 - 솔론봇(1) 소개 및 구조 설명.txt
    ├── 인공지능 카톡봇 - 솔론봇(1) 소개 및 구조 설명_metadata.json
    ├── 인공지능 카톡봇 - 솔론봇(1) 소개 및 구조 설명_timestamps.txt
    ├── 인공지능 카톡봇 - 솔론봇(1) 소개 및 구조 설명_corrected.txt
    ├── 인공지능 카톡봇 - 솔론봇(1) 소개 및 구조 설명_corrected_metadata.json
    └── 인공지능 카톡봇 - 솔론봇(1) 소개 및 구조 설명_corrected_timestamps.txt
```

### 타임스탬프 파일 형식
```
타임스탬프별 자막 (보정됨)
==================================================

[00:00:00.560 → 00:00:03.520] 안녕하세요. 사실 비주얼 스토리 이어 쓰기 시리즈를 계속 하려고 하는데,
[00:00:03.520 → 00:00:12.839] 중간에 문제가 생겨서,
[00:00:12.839 → 00:00:14.039] 이번에 4번까지 하고, 5번 찍었고 올려야 되는데, 쉽지 않더라고요.
```

## ⚙️ 기술 스택

|  컴포넌트 | 도구/라이브러리 | 역할 |
|---------|----------------|------|
| **오디오 추출** | `yt-dlp` + `ffmpeg` | YouTube → WAV 변환 |
| **오디오 처리** | `pydub` | 파일 분할, 포맷 변환 |
| **음성인식** | `Groq Whisper Turbo` | 음성 → 텍스트 + 메타데이터 |
| **AI 보정** | `Groq LLM (llama-3.3-70b)` | 텍스트 교정 |
| **환경관리** | `python-dotenv` | API 키 관리 |

## 📊 메타데이터 구조

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
      "text": "안녕하세요. 사실 비주얼 스토리 이어 쓰기 시리즈를 계속 하려고 하는데,",
      "tokens": [50365, 38962, 9820, 13, ...],
      "avg_logprob": -0.4902137,
      "compression_ratio": 0.6944444,
      "no_speech_prob": 1.5166007e-10
    }
  ]
}
```

## 🛠️ 고급 기능

### 기존 파일 보정
```python
from main import correct_existing_transcript_file

# 기존 타임스탬프 파일 보정
corrected_file = correct_existing_transcript_file(
    './result/비디오제목_timestamps.txt',
    use_ai_correction=True
)
```

### 설정 옵션
```python
# 보정 기능 제어
youtube_to_subtitle(
    url,
    output_dir="./result",
    subtitle_format="txt",
    enable_correction=True,      # 텍스트 보정 활성화
    use_ai_correction=True       # AI 기반 보정 활성화
)
```

## 🔧 에러 처리

### 파일 크기 제한 자동 처리
```python
# 24MB 초과 시 자동 분할
if file_size_mb > 24:
    chunks = split_audio_by_size(audio_path, max_size_mb=24)
    # 각 청크별로 개별 처리 후 결합
```

### API 오류 복구
- Groq API 호출 실패 시 부분 결과 저장
- 네트워크 오류 시 재시도 로직
- 임시 파일 자동 정리

## 💡 사용 예시

### 기본 사용
```bash
# 단일 영상 처리
python main.py "YouTube_URL"
```

### 명령행 옵션
```bash
# URL 없이 실행 시 테스트 URL 사용
python main.py

# 환경변수로 API 키 설정
export GROQ_API_KEY=your_api_key_here
python main.py "YouTube_URL"
```

## 📋 요구사항

### 시스템 요구사항
- Python 3.12+
- ffmpeg (오디오 처리용)
- 인터넷 연결 (YouTube 다운로드 및 Groq API)

### Python 패키지
```toml
[project]
dependencies = [
    "groq>=0.26.0",
    "python-dotenv>=1.0.0",
    "yt-dlp>=2024.3.10",
    "pydub>=0.25.1",
]
```

## 🐛 문제 해결

### ffmpeg 설치
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# https://ffmpeg.org/download.html 에서 다운로드
```

### API 키 오류
- Groq 콘솔에서 유효한 API 키 확인
- `.env` 파일 경로 및 형식 확인
- API 사용량 한도 확인

### 음성인식 오류
- 인터넷 연결 상태 확인
- 오디오 파일 품질 확인 (손상된 파일 제외)
- Groq API 서비스 상태 확인

## 📈 성능 최적화

### 처리 속도 향상
- 청크 단위 병렬 처리
- 메모리 효율적인 스트리밍
- 임시 파일 자동 정리

### 품질 향상
- 고품질 오디오 추출 (192kbps WAV)
- 이중 보정 시스템 (패턴 + AI)
- 신뢰도 기반 결과 검증

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 지원

문제가 발생하거나 궁금한 점이 있으시면 GitHub Issues를 통해 문의해 주세요.

---

**⚡ 빠르고 정확한 YouTube 자막 생성을 경험해보세요\!**
