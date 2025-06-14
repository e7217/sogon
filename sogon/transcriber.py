"""
오디오 전사(transcription) 모듈
"""

import os
import logging
from groq import Groq
from .downloader import split_audio_by_size

logger = logging.getLogger(__name__)


def transcribe_audio(audio_file_path, api_key=None):
    """
    Groq Whisper Turbo를 사용하여 오디오 파일을 텍스트로 변환
    큰 파일은 자동으로 분할하여 처리

    Args:
        audio_file_path (str): 오디오 파일 경로
        api_key (str): Groq API 키 (없으면 환경변수에서 가져옴)

    Returns:
        tuple: (변환된 텍스트, 메타데이터 리스트)
    """
    logger.debug(f"transcribe_audio 호출: audio_file_path={audio_file_path}, api_key 제공여부={api_key is not None}")
    
    # API 키 설정
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY")
        logger.debug("API 키를 환경변수에서 가져옴")

    if not api_key:
        logger.error("GROQ_API_KEY가 설정되지 않음")
        raise ValueError(
            "GROQ_API_KEY 환경변수를 설정하거나 api_key 매개변수를 제공하세요."
        )

    # Groq 클라이언트 초기화
    logger.debug("Groq 클라이언트 초기화")
    client = Groq(api_key=api_key)

    try:
        # 파일 크기 확인 및 필요시 분할
        logger.debug(f"오디오 파일 분할 시작: {audio_file_path}")
        audio_chunks = split_audio_by_size(audio_file_path)
        logger.info(f"오디오 파일이 {len(audio_chunks)}개 청크로 분할됨")
        all_transcriptions = []
        all_metadata = []

        for i, chunk_path in enumerate(audio_chunks):
            logger.info(f"청크 {i + 1}/{len(audio_chunks)} 처리 중...")

            # 오디오 파일 열기 및 변환
            logger.debug(f"청크 {i+1} Whisper 전사 시작: {chunk_path}")
            try:
                with open(chunk_path, "rb") as audio_file:
                    response = client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-large-v3-turbo",
                        response_format="verbose_json",  # 메타데이터 포함
                        temperature=0.0,  # 더 일관된 결과
                    )
                logger.debug(f"청크 {i+1} Whisper 전사 성공")
            except Exception as api_error:
                logger.error(f"청크 {i+1} Whisper 전사 실패: {api_error}, 원인: {api_error.__cause__ or '알 수 없음'}")
                logger.debug(f"청크 {i+1} API 오류 상세: {type(api_error).__name__}: {str(api_error)}")
                continue

                # 텍스트와 메타데이터 분리
                transcription_text = response.text
                logger.info(f"청크 {i + 1} 전사 결과: {len(transcription_text)} 문자")
                logger.info(f"청크 {i + 1} 미리보기: {transcription_text[:100]}...")
                
                if not transcription_text.strip():
                    logger.warning(f"청크 {i + 1} 전사 결과가 비어있음")
                
                all_transcriptions.append(transcription_text)
                logger.debug(f"청크 {i + 1} 전사 텍스트 추가 완료")

                # 메타데이터 수집
                segments = getattr(response, "segments", [])
                words = getattr(response, "words", []) if hasattr(response, "words") else []
                
                metadata = {
                    "chunk_number": i + 1,
                    "total_chunks": len(audio_chunks),
                    "language": getattr(response, "language", "auto"),
                    "duration": getattr(response, "duration", None),
                    "segments": segments,
                    "words": words,
                }
                all_metadata.append(metadata)
                
                logger.debug(f"청크 {i + 1} 메타데이터: 언어={metadata['language']}, 지속시간={metadata['duration']}, 세그먼트={len(segments)}개, 단어={len(words)}개")

            # 임시 청크 파일 삭제 (원본이 아닌 경우)
            if chunk_path != audio_file_path:
                try:
                    os.remove(chunk_path)
                    logger.debug(f"청크 {i + 1} 임시 파일 삭제 완료: {chunk_path}")
                except OSError as e:
                    logger.warning(f"청크 {i + 1} 임시 파일 삭제 실패: {e}, 원인: {e.__cause__ or '알 수 없음'}")
                    logger.debug(f"파일 삭제 상세 오류: {type(e).__name__}: {str(e)}")

        # 모든 전사 결과 합치기
        combined_text = " ".join(all_transcriptions)
        logger.info(f"전사 완료: 총 {len(combined_text)} 문자")
        logger.info(f"전사 결과 미리보기: {combined_text[:100]}...")
        
        # 전사 품질 검사
        if len(combined_text.strip()) == 0:
            logger.error("전사 결과가 비어있음")
        elif len(combined_text) < 50:
            logger.warning(f"전사 결과가 너무 짧음: {len(combined_text)}문자")
        else:
            logger.debug(f"전사 품질 검사 통과: {len(combined_text)}문자")
        
        logger.debug(f"리턴 데이터: 텍스트 길이={len(combined_text)}, 메타데이터 청크 수={len(all_metadata)}")
        return combined_text, all_metadata

    except Exception as e:
        logger.error(f"오디오 변환 중 오류 발생: {e}, 원인: {e.__cause__ or '알 수 없음'}")
        logger.debug(f"예외 상세 정보: {type(e).__name__}: {str(e)}")
        import traceback
        logger.debug(f"스택 트레이스:\n{traceback.format_exc()}")
        if e.__cause__:
            logger.debug(f"오디오 변환 근본 원인: {type(e.__cause__).__name__}: {str(e.__cause__)}")
        return None, None
