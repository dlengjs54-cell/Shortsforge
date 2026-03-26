"""
백그라운드 작업 관리자
- 영상 생성은 1~3분 걸리므로 별도 스레드에서 실행
- 진행 상태를 실시간 추적
"""

import threading
import time
import traceback
from datetime import datetime
from collections import OrderedDict

from core.config_loader import Config
from core.project_manager import ProjectManager, Project
from core.pipeline import Pipeline


class TaskManager:
    """백그라운드 작업 큐 관리"""

    def __init__(self, config: Config):
        self.config = config
        self.pm = ProjectManager(config)
        self.pipeline = Pipeline(config)
        self._tasks: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()
        self._queue: list[dict] = []
        self._running = False
        self._worker_thread = None

    # ── 작업 등록 ──

    def create_project(self, topic: str) -> dict:
        """단일 프로젝트 생성 + 큐에 추가"""
        project = self.pm.create(topic)
        task = self._register_task(project)
        self._start_worker()
        return task

    def create_batch(self, topics: list[str]) -> list[dict]:
        """여러 주제 일괄 등록"""
        tasks = []
        for topic in topics:
            topic = topic.strip()
            if not topic or topic.startswith("#"):
                continue
            project = self.pm.create(topic)
            task = self._register_task(project)
            tasks.append(task)
        self._start_worker()
        return tasks

    def resume_project(self, project_id: str, from_stage: str = None) -> dict:
        """실패한 프로젝트 재실행"""
        project = self.pm.load(project_id)
        task = self._register_task(project, resume_from=from_stage)
        self._start_worker()
        return task

    # ── 상태 조회 ──

    def get_task(self, project_id: str) -> dict | None:
        with self._lock:
            return self._tasks.get(project_id)

    def get_all_tasks(self) -> list[dict]:
        with self._lock:
            return list(self._tasks.values())

    def get_projects(self) -> list[dict]:
        """전체 프로젝트 목록 (작업 상태 포함)"""
        projects = self.pm.list_projects()
        result = []
        for p in projects:
            info = {
                "id": p.id,
                "topic": p.topic,
                "status": p.status,
                "is_complete": p.is_complete(),
                "has_video": p.final_video_path.exists(),
                "dir": str(p.dir),
                "created_at": p._manifest.get("created_at", ""),
            }
            # 실행 중인 작업 정보 병합
            with self._lock:
                task = self._tasks.get(p.id)
                if task:
                    info["task_status"] = task["status"]
                    info["task_stage"] = task.get("current_stage", "")
                    info["task_log"] = task.get("log", [])[-5:]  # 최근 5줄
            result.append(info)
        return result

    def get_project_detail(self, project_id: str) -> dict:
        """프로젝트 상세 정보"""
        project = self.pm.load(project_id)
        info = {
            "id": project.id,
            "topic": project.topic,
            "status": project.status,
            "is_complete": project.is_complete(),
            "has_video": project.final_video_path.exists(),
            "has_script": project.script_path.exists(),
            "has_audio": project.audio_path.exists(),
            "dir": str(project.dir),
            "manifest": project._manifest,
        }

        # 스크립트 내용
        if project.script_path.exists():
            import json
            with open(project.script_path, "r", encoding="utf-8") as f:
                info["script"] = json.load(f)

        # 미디어 목록
        if project.media_manifest_path.exists():
            import json
            with open(project.media_manifest_path, "r", encoding="utf-8") as f:
                info["media"] = json.load(f)

        # 오디오 메타
        if project.audio_meta_path.exists():
            import json
            with open(project.audio_meta_path, "r", encoding="utf-8") as f:
                info["audio_meta"] = json.load(f)

        # 실행 중 작업 로그
        with self._lock:
            task = self._tasks.get(project_id)
            if task:
                info["task_status"] = task["status"]
                info["task_log"] = task.get("log", [])

        return info

    def delete_project(self, project_id: str):
        """프로젝트 삭제"""
        import shutil
        project = self.pm.load(project_id)
        shutil.rmtree(project.dir)
        with self._lock:
            self._tasks.pop(project_id, None)

    # ── 내부 로직 ──

    def _register_task(self, project: Project, resume_from: str = None) -> dict:
        task = {
            "project_id": project.id,
            "topic": project.topic,
            "status": "queued",
            "current_stage": "",
            "resume_from": resume_from,
            "created_at": datetime.now().isoformat(),
            "log": [f"[{self._now()}] 큐에 추가됨"],
        }
        with self._lock:
            self._tasks[project.id] = task
            self._queue.append(task)
        return task

    def _start_worker(self):
        """워커 스레드 시작 (이미 실행 중이면 스킵)"""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _worker_loop(self):
        """큐에서 작업을 하나씩 꺼내 실행"""
        while True:
            with self._lock:
                if not self._queue:
                    self._running = False
                    return
                task = self._queue.pop(0)

            project_id = task["project_id"]
            try:
                project = self.pm.load(project_id)
                self._update_task(project_id, status="running", log=f"파이프라인 시작")

                resume_from = task.get("resume_from")
                if not resume_from:
                    resume_from = project.get_resume_stage()

                stages = Project.STAGES
                start_idx = stages.index(resume_from) if resume_from and resume_from in stages else 0

                for i, stage in enumerate(stages):
                    if i < start_idx:
                        continue

                    self._update_task(project_id, current_stage=stage, log=f"[{stage.upper()}] 실행 중...")
                    success = self.pipeline.run_stage(project, stage)

                    if success:
                        self._update_task(project_id, log=f"[{stage.upper()}] ✅ 완료")
                    else:
                        self._update_task(project_id, status="failed", log=f"[{stage.upper()}] ❌ 실패")
                        break
                else:
                    self._update_task(project_id, status="done", current_stage="", log="🎉 영상 생성 완료!")

            except Exception as e:
                error_msg = f"오류: {type(e).__name__}: {e}"
                self._update_task(project_id, status="failed", log=error_msg)
                traceback.print_exc()

    def _update_task(self, project_id: str, **kwargs):
        with self._lock:
            task = self._tasks.get(project_id)
            if not task:
                return
            if "status" in kwargs:
                task["status"] = kwargs["status"]
            if "current_stage" in kwargs:
                task["current_stage"] = kwargs["current_stage"]
            if "log" in kwargs:
                task["log"].append(f"[{self._now()}] {kwargs['log']}")

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%H:%M:%S")
