"""
환경 초기화 - moviepy ImageMagick 경로 자동 감지 (윈도우)
이 파일은 main.py, test_all.py 실행 시 자동 로드됩니다.
"""

import os
import sys
import platform


def setup_imagemagick():
    """윈도우에서 ImageMagick 경로를 자동 감지하여 moviepy에 등록"""
    if platform.system() != "Windows":
        return

    # 이미 환경변수로 설정되어 있으면 스킵
    if os.getenv("IMAGEMAGICK_BINARY"):
        return

    # 일반적인 설치 경로 탐색
    search_paths = [
        r"C:\Program Files\ImageMagick-7*\magick.exe",
        r"C:\Program Files (x86)\ImageMagick-7*\magick.exe",
    ]

    import glob
    for pattern in search_paths:
        matches = glob.glob(pattern)
        if matches:
            magick_path = matches[-1]  # 최신 버전
            os.environ["IMAGEMAGICK_BINARY"] = magick_path
            return

    # 못 찾으면 경고 (치명적이지 않으므로 계속 진행)
    print("⚠️  ImageMagick을 자동으로 찾지 못했습니다.")
    print("   텍스트 오버레이가 작동하지 않을 수 있습니다.")
    print("   WINDOWS_SETUP.md의 2단계를 참고하세요.")


# 모듈 임포트 시 자동 실행
setup_imagemagick()
