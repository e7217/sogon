"""
텍스트 보정 모듈
"""

import os
import re
import logging
from groq import Groq

logger = logging.getLogger(__name__)


def fix_ai_based_corrections(text, api_key=None):
    """
    AI를 이용한 텍스트 후처리 및 보정

    Args:
        text (str): 원본 텍스트
        api_key (str): Groq API 키

    Returns:
        str: 보정된 텍스트
    """
    logger.debug(f"AI 보정 시작: 텍스트 길이={len(text)}, api_key 제공여부={api_key is not None}")
    
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY")
        logger.debug("API 키를 환경변수에서 가져옴")

    if not api_key:
        logger.warning("AI 기반 보정을 위한 API 키가 없습니다. 원본 텍스트를 반환합니다.")
        logger.debug("API 키 없음으로 인해 원본 텍스트 반환")
        return text

    try:
        client = Groq(api_key=api_key)

        # 텍스트가 너무 길면 청크로 나누어 처리
        max_chunk_length = 1500

        logger.info(f"원본 텍스트 길이: {len(text)} 문자")

        if len(text) <= max_chunk_length:
            chunks = [text]
            logger.debug(f"텍스트가 최대 길이 이하로 분할 불필요")
        else:
            logger.debug(f"텍스트가 최대 길이({max_chunk_length})를 초과하여 분할 시작")
            # 문장으로 분할
            sentences = re.split(r"[.!?]\s*", text)

            if len(sentences) <= 1:
                sentences = re.split(r",\s*", text)

            if len(sentences) <= 1:
                sentences = text.split(" ")

            chunks = []
            current_chunk = ""

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                test_chunk = current_chunk + (" " if current_chunk else "") + sentence

                if len(test_chunk) <= max_chunk_length:
                    current_chunk = test_chunk
                else:
                    if current_chunk:
                        chunks.append(current_chunk)

                    if len(sentence) > max_chunk_length:
                        words = sentence.split(" ")
                        temp_chunk = ""
                        for word in words:
                            if len(temp_chunk + " " + word) <= max_chunk_length:
                                temp_chunk += (" " if temp_chunk else "") + word
                            else:
                                if temp_chunk:
                                    chunks.append(temp_chunk)
                                temp_chunk = word
                        if temp_chunk:
                            current_chunk = temp_chunk
                    else:
                        current_chunk = sentence

            if current_chunk:
                chunks.append(current_chunk)
                logger.debug(f"마지막 청크 추가: 길이={len(current_chunk)}")

        logger.info(f"총 {len(chunks)}개의 청크로 분할됨")

        corrected_chunks = []

        for i, chunk in enumerate(chunks):
            logger.info(f"AI 보정 중... ({i + 1}/{len(chunks)}) - 청크 길이: {len(chunk)}")
            logger.debug(f"청크 {i+1} 내용 미리보기: {chunk[:50]}...")

            if not chunk.strip():
                logger.warning(f"청크 {i+1}이 비어있어 건너뜀")
                continue

            prompt = f"""다음은 한국어 음성인식으로 변환된 텍스트입니다. 
음성인식 과정에서 발생할 수 있는 오류들을 자연스럽게 수정해주세요:

1. 잘못 인식된 기술 용어나 고유명사 수정
2. 문법적으로 어색한 부분 자연스럽게 수정
3. 의미가 통하지 않는 단어나 구문 수정
4. 전체적인 문맥과 일치하도록 수정
5. 원본의 의미와 길이를 최대한 유지

원본 텍스트:
{chunk}

수정된 텍스트만 출력해주세요 (설명이나 부가 설명 없이):"""

            logger.debug(f"청크 {i+1} Groq API 호출 시작")
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 한국어 텍스트 교정 전문가입니다. 음성인식 오류를 자연스럽게 수정하되, 원본의 의미와 길이를 최대한 유지해야 합니다.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=3000,
                )
                logger.debug(f"청크 {i+1} API 호출 성공")
            except Exception as api_error:
                logger.error(f"청크 {i+1} API 호출 실패: {api_error}, 원인: {api_error.__cause__ or '알 수 없음'}")
                logger.debug(f"청크 {i+1} API 오류 상세: {type(api_error).__name__}: {str(api_error)}")
                corrected_chunks.append(chunk)  # 원본 청크 사용
                continue

            corrected_chunk = response.choices[0].message.content.strip()
            logger.info(f"청크 {i + 1} 보정 완료: {len(corrected_chunk)} 문자")

            if corrected_chunk:
                corrected_chunks.append(corrected_chunk)
                logger.debug(f"청크 {i+1} 보정 결과 미리보기: {corrected_chunk[:50]}...")
            else:
                logger.warning(f"청크 {i+1} 보정 결과가 비어있음")

        final_result = " ".join(corrected_chunks)
        logger.info(f"최종 보정된 텍스트 길이: {len(final_result)} 문자")
        logger.debug(f"최종 결과 미리보기: {final_result[:100]}...")
        
        # 보정 비율 계산
        if len(text) > 0:
            improvement_ratio = len(final_result) / len(text)
            logger.debug(f"보정 비율: {improvement_ratio:.2f} (원본: {len(text)}, 보정후: {len(final_result)})")
            if improvement_ratio < 0.5:
                logger.warning(f"보정된 텍스트가 원본의 50% 미만입니다 ({improvement_ratio:.2f})")

        return final_result

    except Exception as e:
        logger.error(f"AI 기반 보정 중 오류 발생: {e}, 원인: {e.__cause__ or '알 수 없음'}")
        logger.debug(f"AI 보정 상세 오류: {type(e).__name__}: {str(e)}")
        if e.__cause__:
            logger.debug(f"AI 보정 근본 원인: {type(e.__cause__).__name__}: {str(e.__cause__)}")
        return text


def format_timestamp(seconds):
    """
    초를 HH:mm:ss.SSS 형식으로 변환
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    milliseconds = int((secs % 1) * 1000)
    secs = int(secs)

    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def parse_timestamp(timestamp_str):
    """
    타임스탬프 문자열을 초 단위로 변환
    """
    try:
        parts = timestamp_str.split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        result = hours * 3600 + minutes * 60 + seconds
        logger.debug(f"타임스탬프 파싱: {timestamp_str} -> {result}초")
        return result
    except (ValueError, IndexError) as e:
        logger.warning(f"타임스탬프 파싱 실패: {timestamp_str}, 오류: {e}, 원인: {e.__cause__ or '알 수 없음'}")
        logger.debug(f"타임스탬프 파싱 상세 오류: {type(e).__name__}: {str(e)}")
        return 0.0


def sort_timestamps_and_fix_overlaps(timestamps_data):
    """
    타임스탬프를 시간순으로 정렬하고 겹치는 부분 수정
    """
    logger.debug(f"타임스탬프 정렬 시작: {len(timestamps_data)}개 항목")
    # 시작 시간 기준으로 정렬
    sorted_data = sorted(timestamps_data, key=lambda x: parse_timestamp(x[0]))
    logger.debug(f"타임스탬프 정렬 완료")

    # 겹치는 시간 구간 수정
    fixed_data = []
    for i, (start, end, text) in enumerate(sorted_data):
        start_seconds = parse_timestamp(start)
        end_seconds = parse_timestamp(end)

        # 이전 세그먼트와 겹치는지 확인
        if fixed_data and start_seconds < parse_timestamp(fixed_data[-1][1]):
            logger.debug(f"세그먼트 {i+1} 겹침 감지: {start} < {fixed_data[-1][1]}")
            adjusted_start = fixed_data[-1][1]
            if end_seconds <= parse_timestamp(adjusted_start):
                end_seconds = parse_timestamp(adjusted_start) + 1.0
                adjusted_end = format_timestamp(end_seconds)
                logger.debug(f"세그먼트 {i+1} 종료시간 조정: {end} -> {adjusted_end}")
            else:
                adjusted_end = end

            fixed_data.append((adjusted_start, adjusted_end, text))
        else:
            fixed_data.append((start, end, text))

    logger.debug(f"타임스탬프 겹침 수정 완료: {len(fixed_data)}개 항목")
    return fixed_data


def correct_transcription_text(text, metadata, api_key=None, use_ai=True):
    """
    전사된 텍스트를 AI 기반으로 보정
    """
    logger.debug(f"correct_transcription_text 호출: use_ai={use_ai}, metadata_chunks={len(metadata) if metadata else 0}")
    logger.info("텍스트 보정을 시작합니다...")
    logger.info(f"원본 텍스트 길이: {len(text)} 문자")
    logger.info(f"원본 텍스트 미리보기: {text[:100]}...")

    corrected_text = text

    # AI 기반 보정
    if use_ai:
        logger.info("AI 기반 텍스트 보정...")
        ai_corrected_text = fix_ai_based_corrections(text, api_key)

        # AI 보정 결과가 원본의 50% 이상이어야 사용
        if ai_corrected_text and len(ai_corrected_text.strip()) > len(text) * 0.5:
            corrected_text = ai_corrected_text
            logger.info(f"AI 보정 완료: {len(corrected_text)} 문자")
            quality_ratio = len(ai_corrected_text.strip()) / len(text)
            logger.debug(f"AI 보정 품질 비율: {quality_ratio:.2f}")
        else:
            logger.warning("AI 보정 결과가 너무 짧음 - 원본 텍스트를 사용합니다.")
            if ai_corrected_text:
                logger.debug(f"AI 보정 결과 길이: {len(ai_corrected_text.strip())}, 원본 길이: {len(text)}, 비율: {len(ai_corrected_text.strip()) / len(text):.2f}")
            else:
                logger.debug("AI 보정 결과가 None 또는 비어있음")

    # 타임스탬프 데이터 정리
    logger.info("타임스탬프 정렬 및 보정...")
    logger.debug(f"metadata 청크 수: {len(metadata)}")
    corrected_metadata = []

    for idx, chunk in enumerate(metadata):
        segments = chunk.get("segments", [])
        logger.debug(f"청크 {idx+1} 처리 시작: segments={len(segments)}")
        timestamps_data = []

        for segment in segments:
            start_time = format_timestamp(segment.get("start", 0))
            end_time = format_timestamp(segment.get("end", 0))
            segment_text = segment.get("text", "").strip()

            if segment_text:
                timestamps_data.append((start_time, end_time, segment_text))

        # 타임스탬프 정렬 및 겹침 수정
        logger.debug(f"청크 {idx+1} 타임스탬프 데이터 수: {len(timestamps_data)}")
        fixed_timestamps = sort_timestamps_and_fix_overlaps(timestamps_data)
        if len(fixed_timestamps) != len(timestamps_data):
            logger.warning(f"청크 {idx+1} 타임스탬프 수정 후 개수 변경: {len(timestamps_data)} -> {len(fixed_timestamps)}")

        # 수정된 세그먼트로 메타데이터 업데이트
        updated_segments = []
        for start_time, end_time, segment_text in fixed_timestamps:
            updated_segments.append(
                {
                    "start": parse_timestamp(start_time),
                    "end": parse_timestamp(end_time),
                    "text": segment_text,
                }
            )

        corrected_chunk = chunk.copy()
        corrected_chunk["segments"] = updated_segments
        corrected_metadata.append(corrected_chunk)

    logger.info("텍스트 보정이 완료되었습니다!")
    logger.debug(f"보정 완료: 텍스트 길이={len(corrected_text)}, 메타데이터 청크 수={len(corrected_metadata)}")
    return corrected_text, corrected_metadata
