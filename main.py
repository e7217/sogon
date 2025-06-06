#!/usr/bin/env python3
"""
YouTube 자막 생성기 (간단한 CLI 인터페이스)
패키지 구조로 리팩토링된 버전
"""

import sys
import json
from mtt import youtube_to_subtitle


def show_preview(file_path, title, max_chars=500):
    """파일 내용 미리보기"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()[:max_chars]
            print(f"\n=== {title} ===")
            print(content)
            if len(content) == max_chars:
                print("...")
    except Exception:
        pass


def show_metadata_info(metadata_path):
    """메타데이터 정보 표시"""
    try:
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
    except Exception:
        pass


def main():
    """메인 실행 함수"""
    print("Media to Text (MTT) - YouTube 자막 생성기")
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
            show_preview(subtitle_path, "원본 자막 미리보기")
            
            if corrected_files:
                show_preview(corrected_subtitle_path, "보정된 자막 미리보기")
            
            show_metadata_info(metadata_path)
            
        else:
            print("❌ 자막 생성에 실패했습니다.")
            
    except Exception as e:
        print(f"❌ 오류: {e}")


if __name__ == "__main__":
    main()