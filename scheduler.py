"""
일일 자동 스케줄러
- 매일 지정 시간에 자동으로 주제 생성 → 영상 완성
- 아침에 출근하면 영상이 준비되어 있는 구조
- 윈도우 작업 스케줄러 연동 지원
"""

import sys
import json
import time
import schedule
import logging
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import core.env_setup  # noqa: F401
from core.config_loader import Config
from core.project_manager import ProjectManager
from core.pipeline import Pipeline
from modules.topic_gen import TopicGenerator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "output" / "scheduler.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("scheduler")


class DailyScheduler:
    """매일 자동 영상 생성"""

    def __init__(self, config: Config):
        self.config = config
        self.pm = ProjectManager(config)
        self.pipeline = Pipeline(config)
        self.topic_gen = TopicGenerator(config)

        # 스케줄 설정
        sched = config.get("scheduler", default={})
        self.run_time = sched.get("run_time", "06:00")
        self.daily_count = sched.get("daily_count", 1)
        self.enabled = sched.get("enabled", True)

    def run_daily_job(self):
        """일일 작업: 주제 생성 → 영상 생성"""
        log.info("=" * 50)
        log.info(f"📅 일일 자동 생성 시작 ({self.daily_count}편)")
        log.info("=" * 50)

        results = {"success": 0, "failed": 0}

        # 1) 대기 주제 확인 (부족하면 자동 생성)
        topics = self.topic_gen.get_next_topics(count=self.daily_count)

        if not topics:
            log.error("❌ 사용할 주제가 없습니다")
            return results

        # 2) 각 주제로 영상 생성
        for i, topic_data in enumerate(topics, 1):
            topic_text = topic_data["topic"]
            log.info(f"\n[{i}/{self.daily_count}] 🎬 {topic_text}")

            try:
                project = self.pm.create(topic_text)
                success = self.pipeline.run(project)

                if success:
                    self.topic_gen.mark_used(topic_text)
                    results["success"] += 1
                    log.info(f"✅ 완료: {project.final_video_path}")
                else:
                    results["failed"] += 1
                    log.error(f"❌ 실패: {project.id}")

            except Exception as e:
                results["failed"] += 1
                log.error(f"❌ 오류: {e}")

        # 3) 결과 리포트
        log.info(f"\n📊 일일 결과: 성공 {results['success']}, 실패 {results['failed']}")
        self._save_daily_report(results, topics)

        return results

    def run_once(self):
        """즉시 1회 실행 (테스트용)"""
        log.info("🚀 수동 1회 실행")
        return self.run_daily_job()

    def start_loop(self):
        """스케줄 루프 시작 (백그라운드 실행)"""
        if not self.enabled:
            log.warning("⚠️  스케줄러가 비활성화 상태입니다 (config: scheduler.enabled)")
            return

        schedule.every().day.at(self.run_time).do(self.run_daily_job)
        log.info(f"⏰ 스케줄러 시작: 매일 {self.run_time}에 {self.daily_count}편 자동 생성")
        log.info(f"   종료: Ctrl+C")

        # 주제 뱅크 상태 출력
        summary = self.topic_gen.get_bank_summary()
        log.info(f"   📦 주제 뱅크: 대기 {summary['pending']}개 / 사용 {summary['used']}개 / 총 {summary['total']}개")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 체크
        except KeyboardInterrupt:
            log.info("\n스케줄러 종료")

    def preview_tomorrow(self):
        """내일 생성될 주제 미리보기"""
        topics = self.topic_gen.get_next_topics(count=self.daily_count)
        print(f"\n📋 다음 자동 생성 주제 ({self.daily_count}편):\n")
        for i, t in enumerate(topics, 1):
            print(f"  {i}. {t['topic']}")
            print(f"     카테고리: {t.get('category', '')} > {t.get('subcategory', '')}")
            print(f"     💡 {t.get('hook_idea', '')}")
            print()

    def refill_topics(self, count: int = 7):
        """주제 뱅크 보충 (일주일치)"""
        print(f"📦 주제 {count}개 보충 생성 중...\n")
        self.topic_gen.generate_daily(count=count)
        summary = self.topic_gen.get_bank_summary()
        print(f"\n📊 주제 뱅크 현황: 대기 {summary['pending']}개 / 총 {summary['total']}개")

    def _save_daily_report(self, results: dict, topics: list):
        """일일 리포트 저장"""
        report_dir = self.config.output_dir / "_reports"
        report_dir.mkdir(exist_ok=True)

        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "results": results,
            "topics": [t["topic"] for t in topics],
        }

        report_path = report_dir / f"report_{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════
# CLI
# ═══════════════════════════════════════

def main():
    """
    사용법:
        python scheduler.py start          매일 자동 실행 시작 (백그라운드)
        python scheduler.py once           지금 즉시 1회 실행
        python scheduler.py preview        다음 주제 미리보기
        python scheduler.py refill         일주일치 주제 보충
        python scheduler.py refill 14      2주치 주제 보충
        python scheduler.py topics         주제 뱅크 현황
        python scheduler.py add "주제"     수동 주제 추가
        python scheduler.py install        윈도우 작업 스케줄러 등록 안내
    """
    import argparse
    parser = argparse.ArgumentParser(description="ShortsForge 일일 자동 스케줄러")
    parser.add_argument("command", choices=["start", "once", "preview", "refill", "topics", "add", "install"],
                        help="실행 명령")
    parser.add_argument("arg", nargs="?", default=None, help="추가 인자")
    args = parser.parse_args()

    config = Config()
    scheduler = DailyScheduler(config)

    if args.command == "start":
        scheduler.start_loop()

    elif args.command == "once":
        scheduler.run_once()

    elif args.command == "preview":
        scheduler.preview_tomorrow()

    elif args.command == "refill":
        count = int(args.arg) if args.arg else 7
        scheduler.refill_topics(count)

    elif args.command == "topics":
        summary = scheduler.topic_gen.get_bank_summary()
        print(f"\n📦 주제 뱅크 현황")
        print(f"   대기: {summary['pending']}개")
        print(f"   사용: {summary['used']}개")
        print(f"   스킵: {summary['skipped']}개")
        print(f"   총계: {summary['total']}개")
        print(f"\n   카테고리별:")
        for cat, cnt in summary["categories"].items():
            print(f"     {cat}: {cnt}개")

        pending = scheduler.topic_gen.get_pending_topics()
        if pending:
            print(f"\n   📋 대기 주제 목록:")
            for i, t in enumerate(pending, 1):
                print(f"     {i}. {t['topic']}  [{t.get('category', '')}]")

    elif args.command == "add":
        if not args.arg:
            print("❌ 주제를 입력하세요: python scheduler.py add \"주제 텍스트\"")
            return
        scheduler.topic_gen.add_manual_topic(args.arg)
        print(f"✅ 수동 주제 추가: {args.arg}")

    elif args.command == "install":
        _print_windows_install_guide()


def _print_windows_install_guide():
    """윈도우 작업 스케줄러 등록 가이드"""
    script_path = Path(__file__).resolve()
    python_hint = sys.executable

    print(f"""
╔══════════════════════════════════════════════════════════╗
║  윈도우 작업 스케줄러로 매일 자동 실행 설정하기           ║
╚══════════════════════════════════════════════════════════╝

방법 1: PowerShell 명령어 (관리자 권한으로 실행)
─────────────────────────────────────────────
아래 명령어를 PowerShell(관리자)에 복사-붙여넣기하세요:

$action = New-ScheduledTaskAction `
    -Execute "{python_hint}" `
    -Argument "{script_path} once" `
    -WorkingDirectory "{script_path.parent}"

$trigger = New-ScheduledTaskTrigger -Daily -At "06:00AM"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName "ShortsForge 자동생성" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "매일 아침 6시 유튜브 쇼츠 자동 생성"

삭제하려면:
Unregister-ScheduledTask -TaskName "ShortsForge 자동생성" -Confirm:$false

방법 2: GUI로 설정
─────────────────
1. [윈도우 키] → "작업 스케줄러" 검색 → 실행
2. 오른쪽 "기본 작업 만들기" 클릭
3. 이름: ShortsForge 자동생성
4. 트리거: 매일, 오전 6:00
5. 동작: 프로그램 시작
   - 프로그램: {python_hint}
   - 인수: {script_path} once
   - 시작 위치: {script_path.parent}
6. 완료

💡 PC가 꺼져있으면 다음 부팅 시 실행됩니다
   (설정에서 "놓친 작업 가능한 빨리 실행" 체크)
""")


if __name__ == "__main__":
    main()
