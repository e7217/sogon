#!/usr/bin/env python3
"""
YouTube 자막 생성기 (간단한 CLI 인터페이스)
패키지 구조로 리팩토링된 버전
"""

import sys
import json
import logging
from sogon import youtube_to_subtitle

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sogon.log', encoding='utf-8')
    ]
)

# 콘솔 로거는 INFO 이상만 출력하도록 설정
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# 파일 로거는 DEBUG 이상 모든 로그 출력
file_handler = logging.FileHandler('sogon.log', mode='a', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s')
file_handler.setFormatter(file_formatter)

# 루트 로거 재설정
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)
root_logger.setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


def show_preview(file_path, title, max_chars=500):
    """파일 내용 미리보기"""
    logger.debug(f"show_preview 호출: file_path={file_path}, title={title}, max_chars={max_chars}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()[:max_chars]
            logger.info(f"\n=== {title} ===")
            logger.info(content)
            if len(content) == max_chars:
                logger.info("...")
                logger.debug(f"파일 내용이 {max_chars}글자로 제한됨")
    except FileNotFoundError:
        logger.error(f"파일을 찾을 수 없음: {file_path}")
    except Exception as e:
        logger.error(f"파일 미리보기 오류: {e}")


def show_metadata_info(metadata_path):
    """메타데이터 정보 표시"""
    logger.debug(f"show_metadata_info 호출: metadata_path={metadata_path}")
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            logger.info("\n=== 메타데이터 정보 ===")
            logger.info(f"총 청크 수: {len(metadata)}")
            if metadata:
                first_chunk = metadata[0]
                logger.info(f"언어: {first_chunk.get('language', 'N/A')}")
                logger.info(f"총 지속시간: {first_chunk.get('duration', 'N/A')}초")
                if first_chunk.get("segments"):
                    segment_count = len(first_chunk['segments'])
                    logger.info(f"세그먼트 수: {segment_count}")
                    logger.debug(f"첫 번째 청크의 세그먼트 상세 정보: {first_chunk.get('segments')[:3] if segment_count > 3 else first_chunk.get('segments')}")
            else:
                logger.warning("메타데이터가 비어있습니다")
    except FileNotFoundError:
        logger.error(f"메타데이터 파일을 찾을 수 없음: {metadata_path}")
    except json.JSONDecodeError as e:
        logger.error(f"메타데이터 JSON 파싱 오류: {e}")
    except Exception as e:
        logger.error(f"메타데이터 정보 표시 오류: {e}")


def main():
    """메인 실행 함수"""
    logger.debug("메인 함수 시작")
    logger.info("SOGON - YouTube 자막 생성기")
    logger.info("=" * 50)

    # 명령행 인수로 URL 받기
    logger.debug(f"명령행 인수 개수: {len(sys.argv)}")
    if len(sys.argv) > 1:
        url = sys.argv[1]
        logger.debug(f"명령행에서 URL 받음: {url}")
    else:
        # 사용자에게 URL 입력받기
        logger.debug("사용자 입력 대기 중...")
        url = input("YouTube URL을 입력하세요: ").strip()
        logger.debug(f"사용자가 입력한 URL: {url}")

    # URL이 없으면 에러 메시지 출력하고 종료
    if not url:
        logger.error("❌ 에러: YouTube URL이 제공되지 않았습니다.")
        logger.info("사용법:")
        logger.info("  python main.py <YouTube_URL>")
        logger.info("  또는 프로그램 실행 후 URL을 입력하세요.")
        logger.debug("빈 URL로 인해 프로그램 종료")
        return

    # 자막 형식 (기본값: txt)
    subtitle_format = "txt"
    logger.debug(f"자막 형식 설정: {subtitle_format}")

    # 기본 출력 디렉토리 (실제 출력은 날짜/시간/제목 폴더로 생성됨)
    base_output_dir = "./result"
    logger.debug(f"기본 출력 디렉토리: {base_output_dir}")

    # 보정 기능 설정
    enable_correction = True
    use_ai_correction = True
    logger.debug(f"보정 기능 설정: enable_correction={enable_correction}, use_ai_correction={use_ai_correction}")

    logger.info("\n자막 생성을 시작합니다...")
    logger.info(f"URL: {url}")
    logger.info(f"형식: {subtitle_format.upper()}")
    logger.info(f"기본 출력 디렉토리: {base_output_dir}")
    logger.info(f"텍스트 보정: {'활성화' if enable_correction else '비활성화'}")
    logger.info(f"AI 보정: {'활성화' if use_ai_correction else '비활성화'}")
    logger.info("-" * 50)

    try:
        # 자막 생성 (보정 기능 포함)
        original_files, corrected_files, actual_output_dir = youtube_to_subtitle(
            url, base_output_dir, subtitle_format, enable_correction, use_ai_correction
        )

        logger.info(f"\n📁 실제 출력 디렉토리: {actual_output_dir}")

        if original_files:
            subtitle_path, metadata_path, timestamp_path = original_files
            logger.info("\n✅ 자막 생성 완료!")
            logger.info(f"원본 자막 파일: {subtitle_path}")
            logger.info(f"원본 메타데이터 파일: {metadata_path}")
            logger.info(f"원본 타임스탬프 파일: {timestamp_path}")
            logger.debug(f"원본 파일들 생성 완료: subtitle={subtitle_path}, metadata={metadata_path}, timestamp={timestamp_path}")

            if corrected_files:
                (
                    corrected_subtitle_path,
                    corrected_metadata_path,
                    corrected_timestamp_path,
                ) = corrected_files
                logger.info(f"\n📝 보정된 자막 파일: {corrected_subtitle_path}")
                logger.info(f"📝 보정된 메타데이터 파일: {corrected_metadata_path}")
                logger.info(f"📝 보정된 타임스탬프 파일: {corrected_timestamp_path}")
                logger.debug(f"보정된 파일들 생성 완료: subtitle={corrected_subtitle_path}, metadata={corrected_metadata_path}, timestamp={corrected_timestamp_path}")
            else:
                logger.warning("보정된 파일이 생성되지 않았습니다")

            # 결과 미리보기
            logger.debug("결과 미리보기 시작")
            show_preview(subtitle_path, "원본 자막 미리보기")

            if corrected_files:
                show_preview(corrected_subtitle_path, "보정된 자막 미리보기")
            else:
                logger.debug("보정된 파일이 없어 미리보기 생략")

            show_metadata_info(metadata_path)

        else:
            logger.error("❌ 자막 생성에 실패했습니다.")

    except Exception as e:
        logger.error(f"❌ 오류: {e}")
        logger.debug(f"예외 상세 정보: {type(e).__name__}: {str(e)}")
        import traceback
        logger.debug(f"스택 트레이스:\n{traceback.format_exc()}")


if __name__ == "__main__":
    logger.debug("프로그램 시작")
    main()
    logger.debug("프로그램 종료")
