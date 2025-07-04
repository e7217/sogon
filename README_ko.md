# SOGON

동영상 URL이나 미디어 파일에서 음성을 추출하고 고급 음성 인식 기술을 이용해 자막을 생성하는 AI 기반 자동화 도구입니다.

## 주요 기능

- **유연한 오디오 추출**: 동영상 URL이나 로컬 미디어 파일에서 고품질 오디오 추출
- **AI 음성인식**: 고급 AI 모델을 사용한 정확한 한국어 음성인식
- **대용량 파일 처리**: 24MB 제한 자동 우회 (파일 분할)
- **정밀한 타임스탬프**: HH:mm:ss.SSS 형식의 세그먼트별 시간 정보
- **지능형 텍스트 보정**: 패턴 기반 + AI 기반 이중 보정
- **체계적인 출력**: 원본/보정본 분리 저장

## 설치

### 방법 1: pipx로 설치 (권장)

```bash
# pipx로 전역 설치
pipx install sogon

# CLI 도구 사용
sogon run "https://www.youtube.com/watch?v=VIDEO_ID"
```

### 패키지 관리

```bash
# 최신 버전으로 업그레이드
pipx upgrade sogon

# 설치된 버전 확인
pipx list

# 제거
pipx uninstall sogon

# 재설치 (필요시)
pipx reinstall sogon
```

### 방법 2: 개발 환경 설정

```bash
# 저장소 클론 및 의존성 설치
git clone <repository-url>
cd sogon
uv sync
```

## 빠른 시작

### 1. API 키 설정

`.env` 파일을 생성하고 API 키를 설정하세요:

```bash
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # 선택사항: AI 텍스트 보정용
```

### 2. 기본 사용법

```bash
# 동영상 URL 처리
sogon run "https://www.youtube.com/watch?v=VIDEO_ID"

# 로컬 미디어 파일 처리
sogon run "/path/to/video/file.mp4"
```

## 시스템 아키텍처

```
동영상 URL/파일 → 오디오 추출 → 음성인식 → 텍스트 보정 → 파일 저장
      ↓             ↓            ↓          ↓          ↓
  다운로더       오디오툴     AI음성모델    AI보정    result/
```

## 처리 단계

1. **오디오 추출**: 미디어 처리 도구로 동영상 URL/파일에서 오디오 추출
2. **파일 처리**: API 제한에 맞춰 대용량 파일 분할
3. **음성인식**: 고급 AI 모델로 한국어 텍스트 처리
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

|  컴포넌트 | 기능 | 역할 |
|---------|------|------|
| **오디오 추출** | 미디어 다운로더 + 오디오 처리기 | 동영상 URL/파일 → 오디오 변환 |
| **오디오 처리** | 오디오 라이브러리 | 파일 분할, 포맷 변환 |
| **음성인식** | AI 음성 모델 | 음성 → 텍스트 + 메타데이터 |
| **AI 보정** | 대규모 언어 모델 | 텍스트 교정 |
| **환경관리** | 설정 관리자 | API 키 관리 |

## 출력 파일

도구는 원본과 보정본 버전의 타임스탬프와 메타데이터를 포함한 체계적인 출력 파일을 생성합니다.

## 고급 기능

### 기존 파일 보정
도구는 기존 음성 변환 파일을 AI 기반으로 개선하는 기능을 제공합니다.

### CLI 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--format`, `-f` | 출력 자막 형식 (txt, srt, vtt, json) | txt |
| `--output-dir`, `-o` | 사용자 정의 출력 디렉토리 | ./result |
| `--no-correction` | 텍스트 보정 비활성화 | False |
| `--no-ai-correction` | AI 기반 텍스트 보정 비활성화 | False |
| `--keep-audio` | 다운로드한 오디오 파일 보관 | False |
| `--translate` | 자막 번역 활성화 | False |
| `--target-language`, `-t` | 번역 대상 언어 | None |
| `--source-language`, `-s` | Whisper용 소스 언어 | 자동 감지 |
| `--log-level` | 로깅 레벨 (DEBUG, INFO, WARNING, ERROR) | INFO |

## 에러 처리

- 대용량 파일에 대한 자동 분할 (>24MB)
- 실패 시 부분 결과 저장
- 임시 파일 자동 정리

## CLI 사용 예시

### 기본 사용
```bash
# 동영상 URL 처리
sogon run "https://www.youtube.com/watch?v=VIDEO_ID"

# 로컬 미디어 파일 처리
sogon run "/path/to/video/file.mp4"
```

### 고급 옵션
```bash
# 출력 형식 지정
sogon run "video.mp4" --format srt

# 텍스트 보정 비활성화
sogon run "video.mp4" --no-correction

# 사용자 정의 출력 디렉토리 설정
sogon run "video.mp4" --output-dir ./my-results

# 다운로드한 오디오 파일 보관
sogon run "https://youtube.com/watch?v=..." --keep-audio

# 한국어로 번역 활성화
sogon run "video.mp4" --translate --target-language ko

# 더 나은 전사를 위한 소스 언어 설정
sogon run "video.mp4" --source-language en

# 로깅 레벨 조정
sogon run "video.mp4" --log-level DEBUG
```

### 번역 기능
```bash
# 지원되는 언어 목록 확인
sogon list-languages

# 다양한 언어로 번역
sogon run "video.mp4" --translate --target-language en  # 영어
sogon run "video.mp4" --translate --target-language ko  # 한국어
```

### 출력 형식
```bash
# 다양한 자막 형식
sogon run "video.mp4" --format txt   # 일반 텍스트 (기본값)
sogon run "video.mp4" --format srt   # SubRip 자막 형식
sogon run "video.mp4" --format vtt   # WebVTT 형식
sogon run "video.mp4" --format json  # 메타데이터 포함 JSON 형식
```


## 요구사항

### 시스템 요구사항
- Python 3.12+
- 오디오 처리 도구
- 인터넷 연결 (동영상 URL 다운로드 및 AI API 접근)

### 종속성
프로젝트는 오디오 처리, AI 통합, 설정 관리를 위한 다양한 Python 패키지가 필요합니다. 구체적인 요구사항은 프로젝트 설정 파일을 참조하세요.

## 문제 해결

- **오디오 도구**: 패키지 매니저를 통해 필요한 오디오 처리 도구 설치
- **API 키**: `.env` 파일에 유효한 AI 서비스 API 키 설정
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
