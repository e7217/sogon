# 동영상 자막 생성기 (Groq Whisper Turbo)

동영상 URL이나 미디어 파일에서 음성을 추출하고 Groq Whisper Turbo를 이용해 자막을 생성하는 AI 기반 자동화 도구입니다.

## 주요 기능

- **유연한 오디오 추출**: yt-dlp를 통한 동영상 URL이나 로컬 미디어 파일에서 고품질 오디오 추출
- **AI 음성인식**: Groq Whisper Turbo로 정확한 한국어 음성인식
- **대용량 파일 처리**: 24MB 제한 자동 우회 (파일 분할)
- **정밀한 타임스탬프**: HH:mm:ss.SSS 형식의 세그먼트별 시간 정보
- **지능형 텍스트 보정**: 패턴 기반 + AI 기반 이중 보정
- **체계적인 출력**: 원본/보정본 분리 저장

## 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치
uv sync
```

### 2. API 키 설정

`.env` 파일을 생성하고 Groq API 키를 설정하세요:

```bash
GROQ_API_KEY=your_groq_api_key_here
```

### 3. 실행

```bash
# 동영상 URL 처리
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"

# 로컬 미디어 파일 처리
python main.py "/path/to/video/file.mp4"
```

## 시스템 아키텍처

```
동영상 URL/파일 → 오디오 추출 → 음성인식 → 텍스트 보정 → 파일 저장
      ↓             ↓            ↓          ↓          ↓
    yt-dlp      ffmpeg     Groq Whisper   AI보정    result/
```

## 처리 단계

1. **오디오 추출**: yt-dlp + ffmpeg로 동영상 URL/파일에서 오디오 추출
2. **파일 처리**: 24MB API 제한에 맞춰 대용량 파일 분할
3. **음성인식**: Groq Whisper Turbo로 한국어 텍스트 처리
4. **텍스트 보정**: 패턴 기반 및 AI 기반 보정 적용
5. **출력 생성**: 원본/보정본 타임스탬프와 함께 저장

## 출력 파일 구조

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

### 타임스탬프 파일 형식
```
타임스탬프별 자막 (보정됨)
==================================================

[00:00:00.560 → 00:00:03.520] 안녕하세요. 사실 비주얼 스토리 이어 쓰기 시리즈를 계속 하려고 하는데,
[00:00:03.520 → 00:00:12.839] 중간에 문제가 생겨서,
[00:00:12.839 → 00:00:14.039] 이번에 4번까지 하고, 5번 찍었고 올려야 되는데, 쉽지 않더라고요.
```

## 기술 스택

|  컴포넌트 | 도구/라이브러리 | 역할 |
|---------|----------------|------|
| **오디오 추출** | `yt-dlp` + `ffmpeg` | 동영상 URL/파일 → WAV 변환 |
| **오디오 처리** | `pydub` | 파일 분할, 포맷 변환 |
| **음성인식** | `Groq Whisper Turbo` | 음성 → 텍스트 + 메타데이터 |
| **AI 보정** | `Groq LLM (llama-3.3-70b)` | 텍스트 교정 |
| **환경관리** | `python-dotenv` | API 키 관리 |

## 출력 파일

도구는 원본과 보정본 버전의 타임스탬프와 메타데이터를 포함한 체계적인 출력 파일을 생성합니다.

## 고급 기능

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

## 에러 처리

- 대용량 파일에 대한 자동 분할 (>24MB)
- 실패 시 부분 결과 저장
- 임시 파일 자동 정리

## 사용 예시

### 기본 사용
```bash
# 동영상 URL 처리
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"

# 로컬 미디어 파일 처리
python main.py "/path/to/video.mp4"
```


## 요구사항

### 시스템 요구사항
- Python 3.12+
- ffmpeg (오디오 처리용)
- 인터넷 연결 (동영상 URL 다운로드 및 Groq API)

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

## 문제 해결

- **ffmpeg**: 패키지 매니저로 설치 또는 공식 사이트에서 다운로드
- **API 키**: `.env` 파일에 유효한 Groq API 키 설정
- **네트워크 문제**: 안정적인 인터넷 연결 확인

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 지원

문제가 발생하거나 궁금한 점이 있으시면 GitHub Issues를 통해 문의해 주세요.
