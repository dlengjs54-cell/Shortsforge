#!/usr/bin/env python3
"""
클라우드 실행기
웹 대시보드 + 일일 스케줄러를 동시에 실행합니다.
Railway / Render / Fly.io 등에서 사용.
"""

import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import core.env_setup  # noqa: F401
from core.config_loader import Config


def start_scheduler(config):
    """백그라운드 스레드에서 스케줄러 실행"""
    try:
        from scheduler import DailyScheduler
        scheduler = DailyScheduler(config)

        # 대기 주제가 없으면 초기 보충
        summary = scheduler.topic_gen.get_bank_summary()
        if summary["pending"] < 3:
            print("📦 초기 주제 보충 중...")
            scheduler.topic_gen.generate_daily(count=5)

        scheduler.start_loop()
    except Exception as e:
        print(f"⚠️  스케줄러 오류 (웹은 계속 실행됨): {e}")


def main():
    config = Config()
    port = int(os.environ.get("PORT", 5000))

    # 스케줄러를 백그라운드 스레드로 실행
    sched_enabled = config.get("scheduler", "enabled", default=True)
    if sched_enabled:
        sched_thread = threading.Thread(target=start_scheduler, args=(config,), daemon=True)
        sched_thread.start()
        print(f"⏰ 스케줄러 백그라운드 시작")

    # Flask 웹 서버 실행 (메인 스레드)
    from web.app import app

    print(f"""
╔══════════════════════════════════════════╗
║     🎬 ShortsForge Cloud                ║
║     Port: {port}                          ║
╚══════════════════════════════════════════╝
    """)

    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
