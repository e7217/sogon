"""
유틸리티 함수들
"""

import os
import json
import re
from datetime import datetime
from .corrector import format_timestamp, correct_transcription_text


def create_output_directory(base_dir="./result", video_title=None):
    """
    yyyyMMDD_HHmmss_타이틀 형식으로 출력 디렉토리 생성
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if video_title:
        safe_title = re.sub(r'[<>:"/\\|?*]', '', video_title)[:50]
        folder_name = f"{timestamp}_{safe_title}"
    else:
        folder_name = timestamp
    
    output_dir = os.path.join(base_dir, folder_name)
    os.makedirs(output_dir, exist_ok=True)
    
    return output_dir


def extract_timestamps_and_text(metadata):
    """
    메타데이터에서 타임스탬프와 텍스트 추출
    """
    timestamps_data = []
    
    for chunk in metadata:
        segments = chunk.get('segments', [])
        for segment in segments:
            start_time = format_timestamp(segment.get('start', 0))
            end_time = format_timestamp(segment.get('end', 0))
            text = segment.get('text', '').strip()
            
            if text:
                timestamps_data.append((start_time, end_time, text))
    
    return timestamps_data


def save_subtitle_and_metadata(text, metadata, output_dir, base_filename, format="txt", 
                              correction_enabled=True, use_ai_correction=True):
    """
    자막과 메타데이터를 파일로 저장 (보정 기능 포함)
    """
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