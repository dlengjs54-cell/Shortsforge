"""
로컬 파일 기반 미디어 Provider
리키항공 자체 촬영 영상이나 수동 준비 클립 사용
"""

import shutil
import random
from pathlib import Path
from modules.media_source.base import MediaProvider
from core.config_loader import Config


class LocalMediaProvider(MediaProvider):

    def __init__(self, config: Config):
        self.local_dir = Path(
            config.get("media", "local_media_dir", default="./assets/local_clips")
        )

    def search_and_download(
        self,
        keyword: str,
        output_dir: Path,
        filename: str,
        duration_sec: float = 5.0,
    ) -> dict | None:
        """로컬 폴더에서 키워드 매칭 또는 랜덤 선택"""
        if not self.local_dir.exists():
            print(f"   ⚠️  로컬 미디어 폴더 없음: {self.local_dir}")
            return None

        video_files = list(self.local_dir.glob("*.mp4"))
        if not video_files:
            print(f"   ⚠️  로컬 미디어 파일 없음")
            return None

        # 키워드 매칭 시도 → 없으면 랜덤
        matched = [f for f in video_files if keyword.lower().replace(" ", "") in f.stem.lower()]
        chosen = matched[0] if matched else random.choice(video_files)

        # 프로젝트 media 폴더로 복사
        ext = chosen.suffix
        output_path = output_dir / f"{filename}{ext}"
        shutil.copy2(chosen, output_path)
        print(f"   📂 로컬 클립 사용: {chosen.name} → {output_path.name}")

        return {
            "file": output_path.name,
            "keyword": keyword,
            "source": "local",
            "original": chosen.name,
            "duration": duration_sec,
        }
