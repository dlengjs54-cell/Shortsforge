#!/usr/bin/env python3
"""
ShortsForge 웹 대시보드 실행기
이 파일을 실행하면 브라우저가 자동으로 열립니다.

사용법:
    python run_web.py
    python run_web.py --port 8080
"""

import sys
import argparse
from pathlib import Path

# 프로젝트 루트
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import core.env_setup  # noqa: F401


def main():
    parser = argparse.ArgumentParser(description="ShortsForge 웹 대시보드")
    parser.add_argument("--port", type=int, default=5000, help="포트 번호 (기본: 5000)")
    parser.add_argument("--no-browser", action="store_true", help="브라우저 자동 열기 비활성화")
    args = parser.parse_args()

    # Flask import 확인
    try:
        from web.app import app
    except ImportError as e:
        print(f"❌ 필수 패키지 누락: {e}")
        print("   pip install flask 를 실행하세요")
        return

    print(f"""
╔══════════════════════════════════════════════╗
║                                              ║
║     🎬  ShortsForge 웹 대시보드              ║
║                                              ║
║     주소: http://localhost:{args.port:<5}             ║
║                                              ║
║     종료: Ctrl+C                             ║
║                                              ║
╚══════════════════════════════════════════════╝
    """)

    if not args.no_browser:
        import webbrowser
        import threading
        threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{args.port}")).start()

    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
