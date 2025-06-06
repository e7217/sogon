"""
YouTube 오디오 다운로드 모듈
"""

import os
import tempfile
import re
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