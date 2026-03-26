"""
Pexels API 기반 스톡 영상 수집
무료 API, 상업적 사용 가능
"""

import requests
from pathlib import Path
from modules.media_source.base import MediaProvider
from core.config_loader import Config


class PexelsMediaProvider(MediaProvider):

    API_BASE = "https://api.pexels.com/videos/search"

    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.get_api_key("PEXELS_API_KEY")
        self.clip_duration = config.get("media", "clip_duration_sec", default=5)

    def search_and_download(
        self,
        keyword: str,
        output_dir: Path,
        filename: str,
        duration_sec: float = None,
    ) -> dict | None:
        """Pexels에서 영상 검색 + 다운로드"""
        duration_sec = duration_sec or self.clip_duration

        print(f"   🔍 Pexels 검색: '{keyword}'")

        headers = {"Authorization": self.api_key}
        params = {
            "query": keyword,
            "per_page": 5,
            "orientation": "portrait",  # 세로형 우선
            "size": "medium",
        }

        try:
            resp = requests.get(self.API_BASE, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"   ⚠️  Pexels API 오류: {e}")
            return None

        videos = data.get("videos", [])
        if not videos:
            print(f"   ⚠️  '{keyword}' 검색 결과 없음")
            return None

        # 첫 번째 적합한 영상 선택
        video = self._select_best(videos)
        if not video:
            return None

        # 다운로드
        video_url = self._get_download_url(video)
        if not video_url:
            return None

        ext = "mp4"
        output_path = output_dir / f"{filename}.{ext}"
        self._download_file(video_url, output_path)

        return {
            "file": output_path.name,
            "keyword": keyword,
            "source": "pexels",
            "pexels_id": video["id"],
            "duration": video.get("duration", duration_sec),
        }

    def _select_best(self, videos: list) -> dict | None:
        """세로형 + 적절한 길이의 영상 선택"""
        for v in videos:
            w = v.get("width", 0)
            h = v.get("height", 0)
            dur = v.get("duration", 0)
            # 세로형 우선, 최소 3초
            if h >= w and dur >= 3:
                return v
        # 세로형 없으면 첫 번째
        return videos[0] if videos else None

    def _get_download_url(self, video: dict) -> str | None:
        """HD 품질 다운로드 URL 추출"""
        files = video.get("video_files", [])
        # HD 우선 → SD 폴백
        for quality in ["hd", "sd"]:
            for f in files:
                if f.get("quality") == quality and f.get("file_type") == "video/mp4":
                    return f["link"]
        # 아무거나
        if files:
            return files[0].get("link")
        return None

    def _download_file(self, url: str, output_path: Path):
        """파일 다운로드"""
        print(f"   ⬇️  다운로드: {output_path.name}")
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
