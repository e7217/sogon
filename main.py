#!/usr/bin/env python3
"""
YouTube 링크에서 음성을 추출하고 Groq Whisper Turbo로 자막 생성
API 키를 환경변수 GROQ_API_KEY에 설정하거나 직접 입력하세요.
"""

import os
import tempfile
import re
from pathlib import Path
from datetime import datetime
from groq import Groq
import yt_dlp
from pydub import AudioSegment

def download_youtube_audio(url, output_dir=None):
    """
    YouTube 비디오에서 오디오를 다운로드
    
    Args:
        url (str): YouTube URL
        output_dir (str): 출력 디렉토리 (없으면 임시 디렉토리 사용)
    
    Returns:
        str: 다운로드된 오디오 파일 경로
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp()
    
    # yt-dlp 옵션 설정
    ydl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'wav',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 비디오 정보 가져오기
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'unknown')
            
            # 파일명에서 특수문자 제거
            safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
            output_path = os.path.join(output_dir, f"{safe_title}.wav")
            
            # 다운로드
            ydl.download([url])
            
            # 다운로드된 파일 찾기
            for file in os.listdir(output_dir):
                if file.endswith('.wav'):
                    return os.path.join(output_dir, file)
            
            return output_path
            
    except Exception as e:
        print(f"YouTube 오디오 다운로드 중 오류 발생: {e}")
        return None

def split_audio_by_size(audio_path, max_size_mb=24):
    """
    오디오 파일을 크기 기준으로 분할
    
    Args:
        audio_path (str): 오디오 파일 경로
        max_size_mb (int): 최대 파일 크기 (MB)
    
    Returns:
        list: 분할된 오디오 파일 경로 목록
    """
    try:
        # 파일 크기 확인
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        
        if file_size_mb <= max_size_mb:
            return [audio_path]
        
        # pydub으로 오디오 로드
        audio = AudioSegment.from_wav(audio_path)
        
        # 청크 길이 계산 (파일 크기 기준)
        total_duration = len(audio)  # 밀리초
        chunk_duration = int((max_size_mb / file_size_mb) * total_duration * 0.9)  # 안전 마진
        
        chunks = []
        temp_dir = os.path.dirname(audio_path)
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        
        # 오디오 분할
        for i, start_time in enumerate(range(0, total_duration, chunk_duration)):
            end_time = min(start_time + chunk_duration, total_duration)
            chunk = audio[start_time:end_time]
            
            chunk_path = os.path.join(temp_dir, f"{base_name}_chunk_{i+1}.wav")
            chunk.export(chunk_path, format="wav")
            chunks.append(chunk_path)
        
        return chunks
        
    except Exception as e:
        print(f"오디오 분할 중 오류 발생: {e}")
        return [audio_path]

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
    # API 키 설정
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        raise ValueError("GROQ_API_KEY 환경변수를 설정하거나 api_key 매개변수를 제공하세요.")
    
    # Groq 클라이언트 초기화
    client = Groq(api_key=api_key)
    
    try:
        # 파일 크기 확인 및 필요시 분할
        audio_chunks = split_audio_by_size(audio_file_path)
        all_transcriptions = []
        all_metadata = []
        
        for i, chunk_path in enumerate(audio_chunks):
            print(f"청크 {i+1}/{len(audio_chunks)} 처리 중...")
            
            # 오디오 파일 열기 및 변환
            with open(chunk_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3-turbo",
                    language="ko",  # 한국어 설정 (자동 감지하려면 제거)
                    response_format="verbose_json"  # 메타데이터 포함
                )
                
                # 텍스트와 메타데이터 분리
                transcription_text = response.text
                print(f"청크 {i+1} 전사 결과: {len(transcription_text)} 문자")
                print(f"청크 {i+1} 미리보기: {transcription_text[:100]}...")
                all_transcriptions.append(transcription_text)
                
                # 메타데이터 수집
                metadata = {
                    "chunk_number": i + 1,
                    "total_chunks": len(audio_chunks),
                    "language": getattr(response, 'language', 'ko'),
                    "duration": getattr(response, 'duration', None),
                    "segments": getattr(response, 'segments', []),
                    "words": getattr(response, 'words', []) if hasattr(response, 'words') else []
                }
                all_metadata.append(metadata)
            
            # 임시 청크 파일 삭제 (원본이 아닌 경우)
            if chunk_path != audio_file_path:
                try:
                    os.remove(chunk_path)
                except:
                    pass
        
        # 모든 전사 결과 합치기
        combined_text = " ".join(all_transcriptions)
        print(f"전사 완료: 총 {len(combined_text)} 문자")
        print(f"전사 결과 미리보기: {combined_text[:100]}...")
        return combined_text, all_metadata
        
    except Exception as e:
        print(f"오디오 변환 중 오류 발생: {e}")
        return None, None

def format_timestamp(seconds):
    """
    초를 HH:mm:ss.SSS 형식으로 변환
    
    Args:
        seconds (float): 초 단위 시간
    
    Returns:
        str: HH:mm:ss.SSS 형식의 시간
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    milliseconds = int((secs % 1) * 1000)
    secs = int(secs)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

def extract_timestamps_and_text(metadata):
    """
    메타데이터에서 타임스탬프와 텍스트 추출
    
    Args:
        metadata (list): 메타데이터 리스트
    
    Returns:
        list: [(시작시간, 끝시간, 텍스트), ...] 형태의 리스트
    """
    timestamps_data = []
    
    for chunk in metadata:
        segments = chunk.get('segments', [])
        for segment in segments:
            start_time = format_timestamp(segment.get('start', 0))
            end_time = format_timestamp(segment.get('end', 0))
            text = segment.get('text', '').strip()
            
            if text:  # 빈 텍스트는 제외
                timestamps_data.append((start_time, end_time, text))
    
    return timestamps_data

def parse_timestamp(timestamp_str):
    """
    타임스탬프 문자열을 초 단위로 변환
    
    Args:
        timestamp_str (str): HH:mm:ss.SSS 형식의 타임스탬프
    
    Returns:
        float: 초 단위 시간
    """
    try:
        parts = timestamp_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    except:
        return 0.0

def fix_common_speech_errors(text):
    """
    일반적인 음성인식 오류 패턴을 보정
    
    Args:
        text (str): 원본 텍스트
    
    Returns:
        str: 보정된 텍스트
    """
    # 일반적인 음성인식 오류 패턴 사전
    corrections = {
        # 기술 용어
        'PAST API': 'FastAPI',
        'past API': 'FastAPI',
        '패스트 API': 'FastAPI',
        '보커': '도커',
        'Raspberry': '라즈베리파이',
        '3포 1램': '3B 1GB',
        '솔롬봇': '솔론봇',
        '제미나이': 'Gemini',
        
        # 일반 단어
        '웅 떠버린': '비어버린',
        '세조립': '세 줄',
        '빵꾸 터진': '뻥 뚫린',
        '공폰': '폰',
        '빈폰': '폰',
        '냅니다': '나옵니다',
        '난잡하게': '이렇게',
        '메신저 보드': '메신저 봇',
        
        # 문법/맞춤법
        '그니까': '그러니까',
        '가지고': '가지고',
        '걸껍니다': '겁니다',
        '되겠죠': '되겠죠',
        '하거든요': '하거든요',
    }
    
    corrected_text = text
    for wrong, correct in corrections.items():
        corrected_text = corrected_text.replace(wrong, correct)
    
    return corrected_text

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
        print("AI 기반 보정을 위한 API 키가 없습니다. 기본 보정만 적용합니다.")
        return text
    
    try:
        client = Groq(api_key=api_key)
        
        # 텍스트가 너무 길면 청크로 나누어 처리
        max_chunk_length = 1500  # 더 작은 청크로 분할
        
        print(f"원본 텍스트 길이: {len(text)} 문자")
        
        if len(text) <= max_chunk_length:
            chunks = [text]
        else:
            # 더 세밀한 분할 방법 사용
            # 먼저 문장으로 분할 시도 (마침표, 느낌표, 물음표)
            sentences = re.split(r'[.!?]\s*', text)
            
            # 문장이 없으면 쉼표로 분할
            if len(sentences) <= 1:
                sentences = re.split(r',\s*', text)
            
            # 그래도 안되면 공백으로 분할
            if len(sentences) <= 1:
                sentences = text.split(' ')
            
            chunks = []
            current_chunk = ""
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                # 현재 청크에 추가했을 때 길이가 초과되는지 확인
                test_chunk = current_chunk + (" " if current_chunk else "") + sentence
                
                if len(test_chunk) <= max_chunk_length:
                    current_chunk = test_chunk
                else:
                    # 현재 청크가 있으면 저장
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    # 문장 자체가 너무 길면 강제로 분할
                    if len(sentence) > max_chunk_length:
                        # 단어 단위로 분할
                        words = sentence.split(' ')
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
            
            # 마지막 청크 추가
            if current_chunk:
                chunks.append(current_chunk)
        
        print(f"총 {len(chunks)}개의 청크로 분할됨")
        
        corrected_chunks = []
        
        for i, chunk in enumerate(chunks):
            print(f"AI 보정 중... ({i+1}/{len(chunks)}) - 청크 길이: {len(chunk)}")
            
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
                    {"role": "system", "content": "당신은 한국어 텍스트 교정 전문가입니다. 음성인식 오류를 자연스럽게 수정하되, 원본의 의미와 길이를 최대한 유지해야 합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=3000  # 더 많은 토큰 허용
            )
            
            corrected_chunk = response.choices[0].message.content.strip()
            print(f"청크 {i+1} 보정 완료: {len(corrected_chunk)} 문자")
            
            if corrected_chunk:
                corrected_chunks.append(corrected_chunk)
        
        final_result = " ".join(corrected_chunks)
        print(f"최종 보정된 텍스트 길이: {len(final_result)} 문자")
        
        return final_result
        
    except Exception as e:
        print(f"AI 기반 보정 중 오류 발생: {e}")
        return text

def sort_timestamps_and_fix_overlaps(timestamps_data):
    """
    타임스탬프를 시간순으로 정렬하고 겹치는 부분 수정
    
    Args:
        timestamps_data (list): [(시작시간, 끝시간, 텍스트), ...] 형태의 리스트
    
    Returns:
        list: 정렬 및 수정된 타임스탬프 데이터
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
            # 겹치는 경우 시작 시간을 이전 세그먼트 끝 시간으로 조정
            adjusted_start = fixed_data[-1][1]
            # 끝 시간이 시작 시간보다 작으면 적절히 조정
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
    전사된 텍스트를 종합적으로 보정
    
    Args:
        text (str): 원본 텍스트
        metadata (list): 메타데이터 리스트
        api_key (str): Groq API 키
        use_ai (bool): AI 기반 보정 사용 여부
    
    Returns:
        tuple: (보정된 텍스트, 보정된 메타데이터)
    """
    print("텍스트 보정을 시작합니다...")
    print(f"원본 텍스트 길이: {len(text)} 문자")
    print(f"원본 텍스트 미리보기: {text[:100]}...")
    
    # 1. 기본 패턴 보정
    print("1단계: 일반적인 음성인식 오류 보정...")
    corrected_text = fix_common_speech_errors(text)
    print(f"1단계 보정 후 길이: {len(corrected_text)} 문자")
    
    # 2. AI 기반 보정 (옵션)
    if use_ai:
        print("2단계: AI 기반 텍스트 보정...")
        print(f"보정 전 텍스트 길이: {len(corrected_text)} 문자")
        ai_corrected_text = fix_ai_based_corrections(corrected_text, api_key)
        print(f"AI 보정 결과 길이: {len(ai_corrected_text) if ai_corrected_text else 0} 문자")
        
        # AI 보정 결과가 원본의 50% 이상이어야 사용
        if ai_corrected_text and len(ai_corrected_text.strip()) > len(corrected_text) * 0.5:
            corrected_text = ai_corrected_text
            print(f"AI 보정 완료: {len(corrected_text)} 문자")
        else:
            print(f"AI 보정 결과가 너무 짧음 (AI: {len(ai_corrected_text) if ai_corrected_text else 0}, 원본: {len(corrected_text)}) - 기본 보정만 사용합니다.")
    
    # 3. 타임스탬프 데이터 보정
    print("3단계: 타임스탬프 정렬 및 보정...")
    corrected_metadata = []
    
    for chunk in metadata:
        # 각 청크의 세그먼트에서 타임스탬프 추출
        segments = chunk.get('segments', [])
        timestamps_data = []
        
        for segment in segments:
            start_time = format_timestamp(segment.get('start', 0))
            end_time = format_timestamp(segment.get('end', 0))
            segment_text = segment.get('text', '').strip()
            
            if segment_text:
                # 세그먼트 텍스트도 보정
                corrected_segment_text = fix_common_speech_errors(segment_text)
                timestamps_data.append((start_time, end_time, corrected_segment_text))
        
        # 타임스탬프 정렬 및 겹침 수정
        fixed_timestamps = sort_timestamps_and_fix_overlaps(timestamps_data)
        
        # 수정된 세그먼트로 메타데이터 업데이트
        updated_segments = []
        for start_time, end_time, segment_text in fixed_timestamps:
            updated_segments.append({
                'start': parse_timestamp(start_time),
                'end': parse_timestamp(end_time),
                'text': segment_text
            })
        
        corrected_chunk = chunk.copy()
        corrected_chunk['segments'] = updated_segments
        corrected_metadata.append(corrected_chunk)
    
    print("텍스트 보정이 완료되었습니다!")
    return corrected_text, corrected_metadata

def save_subtitle_and_metadata(text, metadata, output_dir, base_filename, format="txt", correction_enabled=True, use_ai_correction=True):
    """
    자막과 메타데이터를 파일로 저장 (보정 기능 포함)
    
    Args:
        text (str): 자막 텍스트
        metadata (list): 메타데이터 리스트
        output_dir (str): 출력 디렉토리
        base_filename (str): 기본 파일명
        format (str): 출력 형식 (txt, srt)
        correction_enabled (bool): 텍스트 보정 사용 여부
        use_ai_correction (bool): AI 기반 보정 사용 여부
    
    Returns:
        tuple: (자막 파일 경로, 메타데이터 파일 경로, 타임스탬프 파일 경로, 보정된 파일들 경로)
    """
    import json
    
    try:
        # 원본 파일들 먼저 저장
        subtitle_path = os.path.join(output_dir, f"{base_filename}.{format}")
        metadata_path = os.path.join(output_dir, f"{base_filename}_metadata.json")
        timestamp_path = os.path.join(output_dir, f"{base_filename}_timestamps.txt")
        
        # 원본 자막 저장
        if format == "txt":
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                f.write(text)
        elif format == "srt":
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                f.write("1\n")
                f.write("00:00:00,000 --> 99:59:59,999\n")
                f.write(text)
                f.write("\n")
        
        # 원본 메타데이터 저장
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # 원본 타임스탬프 저장
        timestamps_data = extract_timestamps_and_text(metadata)
        with open(timestamp_path, 'w', encoding='utf-8') as f:
            f.write("타임스탬프별 자막\n")
            f.write("=" * 50 + "\n\n")
            for start_time, end_time, segment_text in timestamps_data:
                f.write(f"[{start_time} → {end_time}] {segment_text}\n")
        
        print(f"원본 자막이 저장되었습니다: {subtitle_path}")
        print(f"원본 메타데이터가 저장되었습니다: {metadata_path}")
        print(f"원본 타임스탬프가 저장되었습니다: {timestamp_path}")
        
        corrected_files = None
        
        # 보정 기능이 활성화된 경우
        if correction_enabled:
            try:
                # 텍스트 보정
                corrected_text, corrected_metadata = correct_transcription_text(
                    text, metadata, use_ai=use_ai_correction
                )
                
                # 보정된 파일들 저장
                corrected_subtitle_path = os.path.join(output_dir, f"{base_filename}_corrected.{format}")
                corrected_metadata_path = os.path.join(output_dir, f"{base_filename}_corrected_metadata.json")
                corrected_timestamp_path = os.path.join(output_dir, f"{base_filename}_corrected_timestamps.txt")
                
                # 보정된 자막 저장
                if format == "txt":
                    with open(corrected_subtitle_path, 'w', encoding='utf-8') as f:
                        f.write(corrected_text)
                elif format == "srt":
                    with open(corrected_subtitle_path, 'w', encoding='utf-8') as f:
                        f.write("1\n")
                        f.write("00:00:00,000 --> 99:59:59,999\n")
                        f.write(corrected_text)
                        f.write("\n")
                
                # 보정된 메타데이터 저장
                with open(corrected_metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(corrected_metadata, f, indent=2, ensure_ascii=False)
                
                # 보정된 타임스탬프 저장
                corrected_timestamps_data = extract_timestamps_and_text(corrected_metadata)
                with open(corrected_timestamp_path, 'w', encoding='utf-8') as f:
                    f.write("타임스탬프별 자막 (보정됨)\n")
                    f.write("=" * 50 + "\n\n")
                    for start_time, end_time, corrected_segment_text in corrected_timestamps_data:
                        f.write(f"[{start_time} → {end_time}] {corrected_segment_text}\n")
                
                corrected_files = (corrected_subtitle_path, corrected_metadata_path, corrected_timestamp_path)
                
                print(f"보정된 자막이 저장되었습니다: {corrected_subtitle_path}")
                print(f"보정된 메타데이터가 저장되었습니다: {corrected_metadata_path}")
                print(f"보정된 타임스탬프가 저장되었습니다: {corrected_timestamp_path}")
                
            except Exception as e:
                print(f"텍스트 보정 중 오류 발생: {e}")
                print("원본 파일만 저장됩니다.")
        
        return subtitle_path, metadata_path, timestamp_path, corrected_files
        
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")
        return None, None, None, None

def create_output_directory(base_dir="./result", video_title=None):
    """
    yyyyMMDD_HHmmss_타이틀 형식으로 출력 디렉토리 생성
    
    Args:
        base_dir (str): 기본 디렉토리
        video_title (str): 비디오 제목
    
    Returns:
        str: 생성된 디렉토리 경로
    """
    # 현재 시간으로 폴더명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 비디오 제목이 있으면 파일명에서 특수문자 제거
    if video_title:
        safe_title = re.sub(r'[<>:"/\\|?*]', '', video_title)[:50]  # 최대 50자로 제한
        folder_name = f"{timestamp}_{safe_title}"
    else:
        folder_name = timestamp
    
    output_dir = os.path.join(base_dir, folder_name)
    os.makedirs(output_dir, exist_ok=True)
    
    return output_dir

def youtube_to_subtitle(url, base_output_dir="./result", subtitle_format="txt", enable_correction=True, use_ai_correction=True):
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
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'unknown')
        
        # 날짜/시간/제목 형식으로 출력 디렉토리 생성
        output_dir = create_output_directory(base_output_dir, video_title)
        print(f"출력 디렉토리 생성: {output_dir}")
        
        print("YouTube에서 오디오 다운로드 중...")
        audio_path = download_youtube_audio(url)
        
        if not audio_path:
            print("오디오 다운로드에 실패했습니다.")
            return None, None
        
        print(f"오디오 다운로드 완료: {audio_path}")
        print("Groq Whisper Turbo로 자막 생성 중...")
        
        # 음성 인식 (메타데이터 포함)
        subtitle_text, metadata = transcribe_audio(audio_path)
        
        if not subtitle_text:
            print("음성 인식에 실패했습니다.")
            return None, None
        
        # 자막 및 메타데이터 파일 저장 (보정 포함)
        video_name = Path(audio_path).stem
        result = save_subtitle_and_metadata(
            subtitle_text, metadata, output_dir, video_name, subtitle_format,
            correction_enabled=enable_correction, use_ai_correction=use_ai_correction
        )
        
        # 임시 오디오 파일 삭제
        try:
            os.remove(audio_path)
            temp_dir = os.path.dirname(audio_path)
            if temp_dir.startswith(tempfile.gettempdir()):
                os.rmdir(temp_dir)
        except:
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

def correct_existing_transcript_file(input_file_path, output_file_path=None, use_ai_correction=True):
    """
    기존 타임스탬프 파일을 보정
    
    Args:
        input_file_path (str): 입력 타임스탬프 파일 경로
        output_file_path (str): 출력 파일 경로 (없으면 _corrected 접미사 추가)
        use_ai_correction (bool): AI 기반 보정 사용 여부
    
    Returns:
        str: 보정된 파일 경로
    """
    try:
        # 출력 파일 경로 설정
        if not output_file_path:
            base_path = os.path.splitext(input_file_path)[0]
            ext = os.path.splitext(input_file_path)[1]
            output_file_path = f"{base_path}_corrected{ext}"
        
        print(f"파일 보정 시작: {input_file_path}")
        
        # 타임스탬프 파일 읽기
        with open(input_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 헤더 라인 찾기
        content_start_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('[') and ' → ' in line:
                content_start_idx = i
                break
        
        header_lines = lines[:content_start_idx] if content_start_idx > 0 else ["타임스탬프별 자막 (보정됨)\n", "=" * 50 + "\n\n"]
        timestamp_lines = lines[content_start_idx:]
        
        # 타임스탬프 데이터 파싱
        timestamps_data = []
        for line in timestamp_lines:
            line = line.strip()
            if line and line.startswith('[') and ' → ' in line:
                # [시작시간 → 끝시간] 텍스트 형식 파싱
                match = re.match(r'\[(.+?) → (.+?)\] (.+)', line)
                if match:
                    start_time, end_time, text = match.groups()
                    timestamps_data.append((start_time.strip(), end_time.strip(), text.strip()))
        
        print(f"총 {len(timestamps_data)}개의 타임스탬프 세그먼트를 찾았습니다.")
        
        # 1. 기본 패턴 보정
        print("1단계: 기본 패턴 보정...")
        corrected_timestamps = []
        for start_time, end_time, text in timestamps_data:
            corrected_text = fix_common_speech_errors(text)
            corrected_timestamps.append((start_time, end_time, corrected_text))
        
        # 2. 타임스탬프 정렬 및 겹침 수정
        print("2단계: 타임스탬프 정렬...")
        sorted_timestamps = sort_timestamps_and_fix_overlaps(corrected_timestamps)
        
        # 3. AI 기반 텍스트 보정 (옵션)
        if use_ai_correction:
            print("3단계: AI 기반 텍스트 보정...")
            # 전체 텍스트 추출
            full_text = " ".join([text for _, _, text in sorted_timestamps])
            corrected_full_text = fix_ai_based_corrections(full_text)
            
            # AI 보정된 텍스트를 다시 세그먼트로 분할 (간단한 방법)
            # 원본 세그먼트 개수와 동일하게 분할 시도
            corrected_sentences = re.split(r'[.!?]\s+', corrected_full_text)
            
            if len(corrected_sentences) >= len(sorted_timestamps):
                # AI 보정 결과를 기존 타임스탬프에 매핑
                final_timestamps = []
                sentence_idx = 0
                
                for start_time, end_time, original_text in sorted_timestamps:
                    if sentence_idx < len(corrected_sentences):
                        corrected_text = corrected_sentences[sentence_idx].strip()
                        if not corrected_text:
                            sentence_idx += 1
                            if sentence_idx < len(corrected_sentences):
                                corrected_text = corrected_sentences[sentence_idx].strip()
                        
                        final_timestamps.append((start_time, end_time, corrected_text))
                        sentence_idx += 1
                    else:
                        final_timestamps.append((start_time, end_time, original_text))
                
                sorted_timestamps = final_timestamps
        
        # 보정된 파일 저장
        with open(output_file_path, 'w', encoding='utf-8') as f:
            # 헤더 작성
            f.write("타임스탬프별 자막 (보정됨)\n")
            f.write("=" * 50 + "\n\n")
            
            # 보정된 타임스탬프 데이터 작성
            for start_time, end_time, text in sorted_timestamps:
                f.write(f"[{start_time} → {end_time}] {text}\n")
        
        print(f"보정된 파일이 저장되었습니다: {output_file_path}")
        return output_file_path
        
    except Exception as e:
        print(f"파일 보정 중 오류 발생: {e}")
        return None

def main():
    """메인 실행 함수"""
    import sys
    
    print("YouTube 자막 생성기 (텍스트 보정 기능 포함)")
    print("=" * 50)
    
    # 명령행 인수로 URL 받기
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # 사용자에게 URL 입력받기
        url = input("YouTube URL을 입력하세요: ").strip()
        
    # URL이 없으면 에러 메시지 출력하고 종료
    if not url:
        print("❌ 에러: YouTube URL이 제공되지 않았습니다.")
        print("사용법:")
        print("  python main.py <YouTube_URL>")
        print("  또는 프로그램 실행 후 URL을 입력하세요.")
        return
    
    # 자막 형식 (기본값: txt)
    subtitle_format = "txt"
    
    # 기본 출력 디렉토리 (실제 출력은 날짜/시간/제목 폴더로 생성됨)
    base_output_dir = "./result"
    
    # 보정 기능 설정
    enable_correction = True
    use_ai_correction = True
    
    print(f"\n자막 생성을 시작합니다...")
    print(f"URL: {url}")
    print(f"형식: {subtitle_format.upper()}")
    print(f"기본 출력 디렉토리: {base_output_dir}")
    print(f"텍스트 보정: {'활성화' if enable_correction else '비활성화'}")
    print(f"AI 보정: {'활성화' if use_ai_correction else '비활성화'}")
    print("-" * 50)
    
    try:
        # 자막 생성 (보정 기능 포함)
        original_files, corrected_files, actual_output_dir = youtube_to_subtitle(
            url, base_output_dir, subtitle_format, enable_correction, use_ai_correction
        )
        
        print(f"\n📁 실제 출력 디렉토리: {actual_output_dir}")
        
        if original_files:
            subtitle_path, metadata_path, timestamp_path = original_files
            print("\n✅ 자막 생성 완료!")
            print(f"원본 자막 파일: {subtitle_path}")
            print(f"원본 메타데이터 파일: {metadata_path}")
            print(f"원본 타임스탬프 파일: {timestamp_path}")
            
            if corrected_files:
                corrected_subtitle_path, corrected_metadata_path, corrected_timestamp_path = corrected_files
                print(f"\n📝 보정된 자막 파일: {corrected_subtitle_path}")
                print(f"📝 보정된 메타데이터 파일: {corrected_metadata_path}")
                print(f"📝 보정된 타임스탬프 파일: {corrected_timestamp_path}")
            
            # 결과 미리보기
            try:
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    content = f.read()[:500]  # 처음 500자만 표시
                    print("\n=== 원본 자막 미리보기 ===")
                    print(content)
                    if len(content) == 500:
                        print("...")
                
                if corrected_files:
                    with open(corrected_subtitle_path, 'r', encoding='utf-8') as f:
                        corrected_content = f.read()[:500]
                        print("\n=== 보정된 자막 미리보기 ===")
                        print(corrected_content)
                        if len(corrected_content) == 500:
                            print("...")
                
                # 메타데이터 미리보기
                import json
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    print(f"\n=== 메타데이터 정보 ===")
                    print(f"총 청크 수: {len(metadata)}")
                    if metadata:
                        first_chunk = metadata[0]
                        print(f"언어: {first_chunk.get('language', 'N/A')}")
                        print(f"총 지속시간: {first_chunk.get('duration', 'N/A')}초")
                        if first_chunk.get('segments'):
                            print(f"세그먼트 수: {len(first_chunk['segments'])}")
            except:
                pass
        else:
            print("❌ 자막 생성에 실패했습니다.")
            
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    main()