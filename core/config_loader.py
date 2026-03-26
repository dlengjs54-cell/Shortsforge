"""
설정 관리 모듈
- default.yaml 로드
- .env API 키 로드
- 설정값 검증 및 접근 인터페이스
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """전역 설정 관리자"""

    def __init__(self, config_path: str = None):
        self._base_dir = Path(__file__).parent.parent  # shortsforge/
        self._config_path = config_path or self._base_dir / "config" / "default.yaml"
        self._data = {}
        self._load()

    def _load(self):
        """YAML 설정 + .env 로드"""
        # 1) YAML 로드
        config_file = Path(self._config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_file}")

        with open(config_file, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}

        # 2) .env 로드 (있으면)
        env_file = self._base_dir / "config" / ".env"
        if env_file.exists():
            load_dotenv(env_file)

        # 3) 경로들을 절대 경로로 변환
        self._resolve_paths()

    def _resolve_paths(self):
        """상대 경로를 프로젝트 루트 기준 절대 경로로 변환"""
        path_keys = [
            ("project", "output_dir"),
            ("style", "font_path"),
            ("style", "bg_music_dir"),
            ("media", "local_media_dir"),
        ]
        for section, key in path_keys:
            if section in self._data and key in self._data[section]:
                raw = self._data[section][key]
                if raw.startswith("./"):
                    self._data[section][key] = str(self._base_dir / raw)

    def get(self, *keys, default=None):
        """
        중첩 키 접근
        사용법: config.get("video", "width")  → 1080
                config.get("tts", "provider")  → "edge"
        """
        current = self._data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def get_api_key(self, name: str) -> str:
        """환경변수에서 API 키 조회"""
        key = os.getenv(name, "")
        if not key:
            raise ValueError(
                f"API 키가 설정되지 않았습니다: {name}\n"
                f"config/.env 파일에 {name}=... 을 추가하세요."
            )
        return key

    @property
    def output_dir(self) -> Path:
        return Path(self.get("project", "output_dir"))

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def validate(self) -> list[str]:
        """설정 검증, 문제 목록 반환"""
        issues = []

        # 필수 섹션 확인
        required_sections = ["video", "script", "tts", "media", "style"]
        for section in required_sections:
            if section not in self._data:
                issues.append(f"필수 섹션 누락: {section}")

        # 비디오 해상도 검증
        w = self.get("video", "width", default=0)
        h = self.get("video", "height", default=0)
        if w <= 0 or h <= 0:
            issues.append(f"비디오 해상도 오류: {w}x{h}")
        if h < w:
            issues.append(f"세로형(9:16) 권장: 현재 {w}x{h}는 가로형입니다")

        # 지원 provider 확인
        valid_script = ["gemini", "openai"]
        valid_tts = ["edge", "google", "elevenlabs"]
        valid_media = ["pexels", "pixabay", "local"]

        sp = self.get("script", "provider")
        if sp and sp not in valid_script:
            issues.append(f"스크립트 provider 미지원: {sp} (가능: {valid_script})")

        tp = self.get("tts", "provider")
        if tp and tp not in valid_tts:
            issues.append(f"TTS provider 미지원: {tp} (가능: {valid_tts})")

        mp = self.get("media", "provider")
        if mp and mp not in valid_media:
            issues.append(f"미디어 provider 미지원: {mp} (가능: {valid_media})")

        return issues

    def dump(self) -> dict:
        """전체 설정 반환 (디버깅용)"""
        return self._data.copy()

    def __repr__(self):
        return f"<Config: {self._config_path}>"
