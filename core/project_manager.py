"""
프로젝트 관리 모듈
- 프로젝트 폴더 생성
- manifest.json 상태 관리
- 중간 산출물 경로 제공
"""

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from core.config_loader import Config


class Project:
    """단일 프로젝트 인스턴스"""

    STAGES = ["script", "tts", "media", "video"]

    def __init__(self, project_dir: Path):
        self.dir = project_dir
        self.manifest_path = project_dir / "manifest.json"
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict:
        if self.manifest_path.exists():
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_manifest(self):
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(self._manifest, f, ensure_ascii=False, indent=2)

    # ── 속성 접근 ──

    @property
    def id(self) -> str:
        return self._manifest.get("id", self.dir.name)

    @property
    def topic(self) -> str:
        return self._manifest.get("topic", "")

    @property
    def status(self) -> dict:
        return self._manifest.get("status", {})

    # ── 파일 경로 ──

    @property
    def script_path(self) -> Path:
        return self.dir / "script.json"

    @property
    def audio_path(self) -> Path:
        return self.dir / "audio.mp3"

    @property
    def audio_meta_path(self) -> Path:
        return self.dir / "audio_meta.json"

    @property
    def media_dir(self) -> Path:
        return self.dir / "media"

    @property
    def media_manifest_path(self) -> Path:
        return self.dir / "media_manifest.json"

    @property
    def final_video_path(self) -> Path:
        return self.dir / "final.mp4"

    # ── 상태 관리 ──

    def get_stage_status(self, stage: str) -> str:
        """단계 상태 조회: pending | running | done | failed"""
        return self._manifest.get("status", {}).get(stage, "pending")

    def update_stage(self, stage: str, status: str, error: str = None):
        """단계 상태 업데이트"""
        if "status" not in self._manifest:
            self._manifest["status"] = {}
        self._manifest["status"][stage] = status
        if error:
            if "errors" not in self._manifest:
                self._manifest["errors"] = {}
            self._manifest["errors"][stage] = error
        self._manifest["updated_at"] = datetime.now().isoformat()
        self._save_manifest()

    def get_resume_stage(self) -> str | None:
        """실패/미완료 단계 중 첫 번째 반환"""
        for stage in self.STAGES:
            if self.get_stage_status(stage) != "done":
                return stage
        return None  # 모든 단계 완료

    def is_complete(self) -> bool:
        return all(
            self.get_stage_status(s) == "done" for s in self.STAGES
        )

    def summary(self) -> str:
        """프로젝트 요약 문자열"""
        lines = [
            f"📁 {self.id}",
            f"   주제: {self.topic}",
        ]
        for stage in self.STAGES:
            status = self.get_stage_status(stage)
            icon = {"done": "✅", "running": "🔄", "failed": "❌"}.get(status, "⬜")
            lines.append(f"   {icon} {stage}: {status}")
        return "\n".join(lines)


class ProjectManager:
    """프로젝트 생성 및 목록 관리"""

    def __init__(self, config: Config):
        self.config = config
        self.output_dir = config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create(self, topic: str) -> Project:
        """새 프로젝트 생성"""
        project_id = self._generate_id(topic)
        project_dir = self.output_dir / project_id

        if project_dir.exists():
            print(f"⚠️  이미 존재하는 프로젝트: {project_id}")
            return Project(project_dir)

        # 폴더 생성
        project_dir.mkdir(parents=True)
        (project_dir / "media").mkdir()

        # manifest 초기화
        manifest = {
            "id": project_id,
            "topic": topic,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": {stage: "pending" for stage in Project.STAGES},
            "config_snapshot": {
                "script_provider": self.config.get("script", "provider"),
                "tts_provider": self.config.get("tts", "provider"),
                "media_provider": self.config.get("media", "provider"),
            },
        }

        manifest_path = project_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print(f"✅ 프로젝트 생성: {project_id}")
        return Project(project_dir)

    def load(self, project_id: str) -> Project:
        """기존 프로젝트 로드"""
        project_dir = self.output_dir / project_id
        if not project_dir.exists():
            raise FileNotFoundError(f"프로젝트를 찾을 수 없습니다: {project_id}")
        return Project(project_dir)

    def list_projects(self) -> list[Project]:
        """전체 프로젝트 목록"""
        projects = []
        for d in sorted(self.output_dir.iterdir()):
            if d.is_dir() and (d / "manifest.json").exists():
                projects.append(Project(d))
        return projects

    def _generate_id(self, topic: str) -> str:
        """주제에서 프로젝트 ID 생성"""
        date_str = datetime.now().strftime("%Y%m%d")
        slug = self._slugify(topic)
        # 최대 50자로 자르기
        slug = slug[:50].rstrip("_")
        return f"{date_str}_{slug}"

    @staticmethod
    def _slugify(text: str) -> str:
        """한국어/영어 혼합 텍스트를 파일명 안전 문자열로 변환"""
        # 공백 → 언더스코어
        text = re.sub(r"\s+", "_", text.strip())
        # 파일명 안전하지 않은 문자 제거 (한글, 영문, 숫자, 언더스코어만 유지)
        text = re.sub(r"[^\w가-힣]", "", text)
        return text
