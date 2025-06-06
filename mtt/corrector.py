"""
텍스트 보정 모듈
"""

import os
import re
from groq import Groq


def fix_ai_based_corrections(text, api_key=None):
    """
    AI를 이용한 텍스트 후처리 및 보정

    Args:
        text (str): 원본 텍스트
        api_key (str): Groq API 키

    Returns:
        str: 보정된 텍스트
    """
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("AI 기반 보정을 위한 API 키가 없습니다. 원본 텍스트를 반환합니다.")
        return text

    try:
        client = Groq(api_key=api_key)

        # 텍스트가 너무 길면 청크로 나누어 처리
        max_chunk_length = 1500

        print(f"원본 텍스트 길이: {len(text)} 문자")

        if len(text) <= max_chunk_length:
            chunks = [text]
        else:
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

        print(f"총 {len(chunks)}개의 청크로 분할됨")

        corrected_chunks = []

        for i, chunk in enumerate(chunks):
            print(f"AI 보정 중... ({i + 1}/{len(chunks)}) - 청크 길이: {len(chunk)}")

            if not chunk.strip():
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

            corrected_chunk = response.choices[0].message.content.strip()
            print(f"청크 {i + 1} 보정 완료: {len(corrected_chunk)} 문자")

            if corrected_chunk:
                corrected_chunks.append(corrected_chunk)

        final_result = " ".join(corrected_chunks)
        print(f"최종 보정된 텍스트 길이: {len(final_result)} 문자")

        return final_result

    except Exception as e:
        print(f"AI 기반 보정 중 오류 발생: {e}")
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
        return hours * 3600 + minutes * 60 + seconds
    except (ValueError, IndexError):
        return 0.0


def sort_timestamps_and_fix_overlaps(timestamps_data):
    """
    타임스탬프를 시간순으로 정렬하고 겹치는 부분 수정
    """
    # 시작 시간 기준으로 정렬
    sorted_data = sorted(timestamps_data, key=lambda x: parse_timestamp(x[0]))

    # 겹치는 시간 구간 수정
    fixed_data = []
    for i, (start, end, text) in enumerate(sorted_data):
        start_seconds = parse_timestamp(start)
        end_seconds = parse_timestamp(end)

        # 이전 세그먼트와 겹치는지 확인
        if fixed_data and start_seconds < parse_timestamp(fixed_data[-1][1]):
            adjusted_start = fixed_data[-1][1]
            if end_seconds <= parse_timestamp(adjusted_start):
                end_seconds = parse_timestamp(adjusted_start) + 1.0
                adjusted_end = format_timestamp(end_seconds)
            else:
                adjusted_end = end

            fixed_data.append((adjusted_start, adjusted_end, text))
        else:
            fixed_data.append((start, end, text))

    return fixed_data


def correct_transcription_text(text, metadata, api_key=None, use_ai=True):
    """
    전사된 텍스트를 AI 기반으로 보정
    """
    print("텍스트 보정을 시작합니다...")
    print(f"원본 텍스트 길이: {len(text)} 문자")
    print(f"원본 텍스트 미리보기: {text[:100]}...")

    corrected_text = text

    # AI 기반 보정
    if use_ai:
        print("AI 기반 텍스트 보정...")
        ai_corrected_text = fix_ai_based_corrections(text, api_key)

        # AI 보정 결과가 원본의 50% 이상이어야 사용
        if ai_corrected_text and len(ai_corrected_text.strip()) > len(text) * 0.5:
            corrected_text = ai_corrected_text
            print(f"AI 보정 완료: {len(corrected_text)} 문자")
        else:
            print("AI 보정 결과가 너무 짧음 - 원본 텍스트를 사용합니다.")

    # 타임스탬프 데이터 정리
    print("타임스탬프 정렬 및 보정...")
    corrected_metadata = []

    for chunk in metadata:
        segments = chunk.get("segments", [])
        timestamps_data = []

        for segment in segments:
            start_time = format_timestamp(segment.get("start", 0))
            end_time = format_timestamp(segment.get("end", 0))
            segment_text = segment.get("text", "").strip()

            if segment_text:
                timestamps_data.append((start_time, end_time, segment_text))

        # 타임스탬프 정렬 및 겹침 수정
        fixed_timestamps = sort_timestamps_and_fix_overlaps(timestamps_data)

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

    print("텍스트 보정이 완료되었습니다!")
    return corrected_text, corrected_metadata
