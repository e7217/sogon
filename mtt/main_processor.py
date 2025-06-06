"""
메인 프로세싱 모듈 - YouTube 링크에서 자막 생성까지의 전체 워크플로우
"""

import os
import tempfile
from pathlib import Path
import yt_dlp
from .downloader import download_youtube_audio
from .transcriber import transcribe_audio
from .utils import create_output_directory, save_subtitle_and_metadata


def youtube_to_subtitle(
    url,
    base_output_dir="./result",
    subtitle_format="txt",
    enable_correction=True,
    use_ai_correction=True,
):
    """
    YouTube 링크에서 자막 생성 (보정 기능 포함)

    Args:
        url (str): YouTube URL
        base_output_dir (str): 기본 출력 디렉토리
        subtitle_format (str): 자막 형식 (txt, srt)
        enable_correction (bool): 텍스트 보정 사용 여부
        use_ai_correction (bool): AI 기반 보정 사용 여부

    Returns:
        tuple: (원본 파일들, 보정된 파일들, 출력 디렉토리)
    """
    try:
        # 먼저 비디오 정보를 가져와서 제목 확인
        print("YouTube 비디오 정보 가져오는 중...")
        ydl_opts = {"quiet": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get("title", "unknown")

        # 날짜/시간/제목 형식으로 출력 디렉토리 생성
        output_dir = create_output_directory(base_output_dir, video_title)
        print(f"출력 디렉토리 생성: {output_dir}")

        print("YouTube에서 오디오 다운로드 중...")
        audio_path = download_youtube_audio(url)

        if not audio_path:
            print("오디오 다운로드에 실패했습니다.")
            return None, None, None

        print(f"오디오 다운로드 완료: {audio_path}")
        print("Groq Whisper Turbo로 자막 생성 중...")

        # 음성 인식 (메타데이터 포함)
        subtitle_text, metadata = transcribe_audio(audio_path)

        if not subtitle_text:
            print("음성 인식에 실패했습니다.")
            return None, None, None

        # 자막 및 메타데이터 파일 저장 (보정 포함)
        video_name = Path(audio_path).stem
        result = save_subtitle_and_metadata(
            subtitle_text,
            metadata,
            output_dir,
            video_name,
            subtitle_format,
            correction_enabled=enable_correction,
            use_ai_correction=use_ai_correction,
        )

        # 임시 오디오 파일 삭제
        try:
            os.remove(audio_path)
            temp_dir = os.path.dirname(audio_path)
            if temp_dir.startswith(tempfile.gettempdir()):
                os.rmdir(temp_dir)
        except OSError:
            pass

        if result and len(result) == 4:
            original_files = result[:3]
            corrected_files = result[3]
            return original_files, corrected_files, output_dir
        else:
            return result[:3] if result else None, None, output_dir

    except Exception as e:
        print(f"자막 생성 중 오류 발생: {e}")
        return None, None, None
