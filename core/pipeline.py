"""
파이프라인 실행기
- 모듈 순차 실행
- 실패 시 중단점 저장 → resume 가능
- 개별 단계 실행 지원
"""

import time
import traceback
from core.config_loader import Config
from core.project_manager import Project


class Pipeline:
    """단계별 파이프라인 실행"""

    STAGES = ["script", "tts", "media", "video"]

    def __init__(self, config: Config):
        self.config = config
        self._runners = {}
        self._register_runners()

    def _register_runners(self):
        """각 단계별 실행 함수 등록 (lazy import)"""
        self._runners = {
            "script": self._run_script,
            "tts": self._run_tts,
            "media": self._run_media,
            "video": self._run_video,
        }

    # ── 실행 ──

    def run(self, project: Project, resume_from: str = None):
        """전체 파이프라인 실행 (또는 특정 단계부터 재개)"""
        print(f"\n🎬 파이프라인 시작: {project.id}")
        print(f"   주제: {project.topic}\n")

        start_index = 0
        if resume_from:
            if resume_from not in self.STAGES:
                raise ValueError(f"알 수 없는 단계: {resume_from} (가능: {self.STAGES})")
            start_index = self.STAGES.index(resume_from)
            print(f"   ▶ '{resume_from}' 단계부터 재개합니다\n")

        for i, stage in enumerate(self.STAGES):
            if i < start_index:
                print(f"   ⏭  {stage}: 건너뜀 (이미 완료)")
                continue

            success = self.run_stage(project, stage)
            if not success:
                print(f"\n❌ '{stage}' 단계에서 실패. 이후 단계 중단.")
                print(f"   재실행: python main.py resume {project.id} --from {stage}")
                return False

        print(f"\n🎉 완료! 영상: {project.final_video_path}")
        return True

    def run_stage(self, project: Project, stage: str) -> bool:
        """개별 단계 실행"""
        if stage not in self._runners:
            raise ValueError(f"알 수 없는 단계: {stage}")

        runner = self._runners[stage]
        print(f"── [{stage.upper()}] 시작 ──")
        project.update_stage(stage, "running")

        start_time = time.time()
        try:
            runner(project)
            elapsed = time.time() - start_time
            project.update_stage(stage, "done")
            print(f"   ✅ 완료 ({elapsed:.1f}초)")
            return True
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"{type(e).__name__}: {e}"
            project.update_stage(stage, "failed", error=error_msg)
            print(f"   ❌ 실패 ({elapsed:.1f}초): {error_msg}")
            traceback.print_exc()
            return False

    # ── 단계별 실행 함수 ──

    def _run_script(self, project: Project):
        from modules.script_gen import create_provider
        provider = create_provider(self.config)
        script_data = provider.generate(project.topic)
        provider.save(script_data, project.script_path)

    def _run_tts(self, project: Project):
        from modules.tts import create_provider
        provider = create_provider(self.config)
        provider.synthesize_from_script(
            script_path=project.script_path,
            audio_path=project.audio_path,
            meta_path=project.audio_meta_path,
        )

    def _run_media(self, project: Project):
        from modules.media_source import create_provider
        provider = create_provider(self.config)
        provider.collect_for_script(
            script_path=project.script_path,
            media_dir=project.media_dir,
            manifest_path=project.media_manifest_path,
        )

    def _run_video(self, project: Project):
        from modules.video_build import compose
        compose(
            project=project,
            config=self.config,
        )
