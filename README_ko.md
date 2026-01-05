# SOGON

동영상 URL이나 미디어 파일에서 음성을 추출하고 고급 음성 인식 기술을 이용해 자막을 생성하는 AI 기반 자동화 도구입니다.

## 주요 기능

- **유연한 오디오 추출**: 동영상 URL이나 로컬 미디어 파일에서 고품질 오디오 추출
- **AI 음성인식**: 고급 AI 모델을 사용한 정확한 한국어 음성인식
- **대용량 파일 처리**: 24MB 제한 자동 우회 (파일 분할)
- **정밀한 타임스탬프**: HH:mm:ss.SSS 형식의 세그먼트별 시간 정보
- **체계적인 출력**: 메타데이터와 함께 정리된 결과 저장

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
OPENAI_API_KEY=your_openai_api_key_here  # 선택사항: 번역용
```

### 2. 기본 사용법

```bash
# 동영상 URL 처리
sogon run "https://www.youtube.com/watch?v=VIDEO_ID"

# 로컬 미디어 파일 처리
sogon run "/path/to/video/file.mp4"
```

## 설정

기본 동작을 영구적으로 설정할 수 있습니다:

```bash
# 모든 설정 조회
sogon config get

# 기본 출력 형식 설정
sogon config set default_subtitle_format srt

# 기본 출력 디렉토리 설정
sogon config set output_base_dir ~/subtitles

# 번역 기본 활성화
sogon config set enable_translation true

# 상세 옵션 및 범위 조회
sogon config get -v

# 기본값으로 초기화
sogon config reset
```

설정은 `~/.sogon/config.yaml`에 저장됩니다.

### 설정 가능한 항목

| 키 | 설명 | 기본값 |
|----|------|--------|
| `output_base_dir` | 출력 디렉토리 | ./result |
| `default_subtitle_format` | 자막 형식 (txt/srt/vtt/json) | txt |
| `transcription_provider` | 제공자 (groq/openai/stable-whisper) | groq |
| `enable_translation` | 기본 번역 활성화 | false |
| `default_translation_language` | 번역 대상 언어 | ko |
| `default_source_language` | 소스 언어 | auto |
| `log_level` | 로깅 레벨 | INFO |
| `keep_temp_files` | 임시 파일 보관 | false |
| `max_workers` | 동시 작업자 수 (1-16) | 4 |
| `max_chunk_size_mb` | 오디오 청크 크기 (1-100) | 24 |

**로컬 모델 설정:**

| 키 | 설명 | 기본값 |
|----|------|--------|
| `local_model_name` | 모델 (tiny~large-v3-turbo) | base |
| `local_device` | 장치 (cpu/cuda/mps) | cuda |
| `local_compute_type` | 정밀도 (int8~float32) | float16 |
| `local_beam_size` | 빔 크기 (1-10) | 5 |
| `local_temperature` | 온도 (0.0-1.0) | 0.0 |
| `local_vad_filter` | VAD 필터 | false |

## 시스템 아키텍처

```
동영상 URL/파일 → 오디오 추출 → 음성인식 → 파일 저장
      ↓             ↓            ↓         ↓
  다운로더       오디오툴     AI음성모델   result/
```

## 처리 단계

1. **오디오 추출**: 미디어 처리 도구로 동영상 URL/파일에서 오디오 추출
2. **파일 처리**: API 제한에 맞춰 대용량 파일 분할
3. **음성인식**: 고급 AI 모델로 텍스트 처리
4. **출력 생성**: 타임스탬프와 함께 결과 저장

## 출력 파일 구조

**날짜/시간/제목별 정리:**
```
result/
└── yyyyMMDD_HHmmss_비디오제목/          # 각 비디오별 타임스탬프 폴더
    ├── 비디오제목.txt                  # 연속 텍스트
    ├── 비디오제목_metadata.json        # 세그먼트 메타데이터
    └── 비디오제목_timestamps.txt       # 타임스탬프별 텍스트
```

### 타임스탬프 파일 형식
```
타임스탬프별 자막
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
| **번역** | 대규모 언어 모델 | 자막 번역 |
| **환경관리** | 설정 관리자 | API 키 및 설정 관리 |

## 출력 파일

도구는 타임스탬프와 메타데이터를 포함한 체계적인 출력 파일을 생성합니다.

## CLI 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--format`, `-f` | 출력 자막 형식 (txt, srt, vtt, json) | txt |
| `--output-dir`, `-o` | 사용자 정의 출력 디렉토리 | ./result |
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
