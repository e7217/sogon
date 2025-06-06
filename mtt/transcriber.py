"""
오디오 전사(transcription) 모듈
"""

import os
from groq import Groq
from .downloader import split_audio_by_size


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
                    response_format="verbose_json",  # 메타데이터 포함
                    temperature=0.0  # 더 일관된 결과
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
                    "language": getattr(response, 'language', 'auto'),
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