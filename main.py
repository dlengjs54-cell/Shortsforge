#!/usr/bin/env python3
"""
ShortsForge — 유튜브 쇼츠 자동 생성 CLI

사용법:
    python main.py create "주제"            새 프로젝트 생성 + 전체 실행
    python main.py resume <ID> --from tts   실패 지점부터 재실행
    python main.py run-stage script --topic "주제"  개별 단계 테스트
    python main.py batch topics.txt         주제 목록 일괄 생성
    python main.py list                     프로젝트 목록
    python main.py config show              현재 설정 확인
"""

import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 윈도우 ImageMagick 자동 감지
import core.env_setup  # noqa: F401

from core.config_loader import Config
from core.project_manager import ProjectManager, Project
from core.pipeline import Pipeline


def cmd_create(args, config: Config):
    """새 프로젝트 생성 + 파이프라인 실행"""
    topic = args.topic
    if not topic:
        print("❌ 주제를 입력하세요: python main.py create \"주제\"")
        return

    pm = ProjectManager(config)
    project = pm.create(topic)

    pipeline = Pipeline(config)
    success = pipeline.run(project)

    if success:
        print(f"\n🎉 영상 생성 완료!")
        print(f"   📁 {project.dir}")
        print(f"   🎬 {project.final_video_path}")


def cmd_resume(args, config: Config):
    """기존 프로젝트 특정 단계부터 재실행"""
    pm = ProjectManager(config)
    project = pm.load(args.project_id)

    resume_from = args.stage
    if not resume_from:
        # 자동 감지: 실패/미완료 첫 단계
        resume_from = project.get_resume_stage()
        if not resume_from:
            print("✅ 이미 모든 단계가 완료된 프로젝트입니다.")
            return
        print(f"   자동 감지: '{resume_from}' 단계부터 재개합니다")

    pipeline = Pipeline(config)
    pipeline.run(project, resume_from=resume_from)


def cmd_run_stage(args, config: Config):
    """개별 단계만 실행 (테스트/디버깅용)"""
    stage = args.stage

    if stage == "script":
        if not args.topic:
            print("❌ --topic 필요: python main.py run-stage script --topic \"주제\"")
            return
        from modules.script_gen import create_provider
        provider = create_provider(config)
        result = provider.generate(args.topic)
        # 임시 저장
        output = PROJECT_ROOT / "output" / "_test_script.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        provider.save(result, output)
        print(f"\n결과: {output}")

    elif stage == "tts":
        script_path = Path(args.input) if args.input else PROJECT_ROOT / "output" / "_test_script.json"
        if not script_path.exists():
            print(f"❌ 스크립트 파일 없음: {script_path}")
            return
        from modules.tts import create_provider
        provider = create_provider(config)
        audio_out = script_path.parent / "test_audio.mp3"
        meta_out = script_path.parent / "test_audio_meta.json"
        provider.synthesize_from_script(script_path, audio_out, meta_out)

    else:
        print(f"❌ run-stage는 현재 'script', 'tts'만 지원합니다")


def cmd_batch(args, config: Config):
    """주제 목록 파일로 일괄 생성"""
    topics_file = Path(args.file)
    if not topics_file.exists():
        print(f"❌ 파일 없음: {topics_file}")
        return

    with open(topics_file, "r", encoding="utf-8") as f:
        topics = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"📋 {len(topics)}개 주제 일괄 처리 시작\n")

    pm = ProjectManager(config)
    pipeline = Pipeline(config)
    results = {"success": 0, "failed": 0}

    for i, topic in enumerate(topics, 1):
        print(f"\n{'='*50}")
        print(f"[{i}/{len(topics)}] {topic}")
        print(f"{'='*50}")

        project = pm.create(topic)
        success = pipeline.run(project)
        results["success" if success else "failed"] += 1

    print(f"\n📊 일괄 처리 완료: 성공 {results['success']}, 실패 {results['failed']}")


def cmd_list(args, config: Config):
    """프로젝트 목록 표시"""
    pm = ProjectManager(config)
    projects = pm.list_projects()

    if not projects:
        print("📭 프로젝트가 없습니다.")
        return

    print(f"\n📁 프로젝트 목록 ({len(projects)}개)\n")
    for p in projects:
        print(p.summary())
        print()


def cmd_config(args, config: Config):
    """설정 표시/검증"""
    if args.action == "show":
        import yaml
        print(yaml.dump(config.dump(), allow_unicode=True, default_flow_style=False))
    elif args.action == "validate":
        issues = config.validate()
        if issues:
            print("⚠️  설정 문제:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ 설정에 문제 없습니다.")


def main():
    parser = argparse.ArgumentParser(
        prog="ShortsForge",
        description="유튜브 쇼츠 자동 생성 도구",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="설정 파일 경로 (기본: config/default.yaml)",
    )

    subparsers = parser.add_subparsers(dest="command", help="명령어")

    # create
    p_create = subparsers.add_parser("create", help="새 쇼츠 생성")
    p_create.add_argument("topic", type=str, help="쇼츠 주제")

    # resume
    p_resume = subparsers.add_parser("resume", help="실패 지점부터 재실행")
    p_resume.add_argument("project_id", type=str, help="프로젝트 ID")
    p_resume.add_argument("--from", dest="stage", type=str, default=None,
                          help="시작 단계 (script|tts|media|video)")

    # run-stage
    p_stage = subparsers.add_parser("run-stage", help="개별 단계 실행")
    p_stage.add_argument("stage", type=str, help="단계 (script|tts|media|video)")
    p_stage.add_argument("--topic", type=str, default=None, help="주제 (script 단계용)")
    p_stage.add_argument("--input", type=str, default=None, help="입력 파일 경로")

    # batch
    p_batch = subparsers.add_parser("batch", help="주제 목록 일괄 생성")
    p_batch.add_argument("file", type=str, help="주제 목록 파일 경로 (한 줄에 하나)")

    # list
    subparsers.add_parser("list", help="프로젝트 목록")

    # config
    p_config = subparsers.add_parser("config", help="설정 확인")
    p_config.add_argument("action", choices=["show", "validate"], help="show|validate")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 설정 로드
    config = Config(args.config)

    # 명령어 라우팅
    commands = {
        "create": cmd_create,
        "resume": cmd_resume,
        "run-stage": cmd_run_stage,
        "batch": cmd_batch,
        "list": cmd_list,
        "config": cmd_config,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args, config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
