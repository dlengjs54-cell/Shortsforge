"""
미디어 소스 Provider 추상 클래스
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path


class MediaProvider(ABC):
    """미디어(영상/이미지) 수집 인터페이스"""

    @abstractmethod
    def search_and_download(
        self,
        keyword: str,
        output_dir: Path,
        filename: str,
        duration_sec: float = 5.0,
    ) -> dict | None:
        """
        키워드로 검색 후 다운로드
        Returns: {"file": str, "keyword": str, "source": str, "duration": float} or None
        """
        pass

    def collect_for_script(
        self,
        script_path: Path,
        media_dir: Path,
        manifest_path: Path,
    ):
        """script.json의 visual_keyword를 기반으로 클립 수집"""
        with open(script_path, "r", encoding="utf-8") as f:
            script = json.load(f)

        media_dir.mkdir(parents=True, exist_ok=True)
        clips = []

        # hook용 클립
        hook_keyword = self._extract_keyword_from_text(script.get("hook", ""))
        clip = self.search_and_download(
            keyword=hook_keyword,
            output_dir=media_dir,
            filename="clip_hook",
        )
        if clip:
            clips.append(clip)

        # body 항목별 클립
        for item in script.get("body", []):
            keyword = item.get("visual_keyword", "")
            if not keyword:
                keyword = self._extract_keyword_from_text(item.get("text", ""))

            clip = self.search_and_download(
                keyword=keyword,
                output_dir=media_dir,
                filename=f"clip_{item['order']:02d}",
            )
            if clip:
                clips.append(clip)

        # cta용 클립
        cta_keyword = "business consultation travel agency"
        clip = self.search_and_download(
            keyword=cta_keyword,
            output_dir=media_dir,
            filename="clip_cta",
        )
        if clip:
            clips.append(clip)

        # manifest 저장
        manifest = {"clips": clips, "total_clips": len(clips)}
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print(f"   🎞  미디어 수집 완료: {len(clips)}개 클립")

    @staticmethod
    def _extract_keyword_from_text(text: str) -> str:
        """한국어 텍스트에서 영문 검색 키워드 추출 (기본 매핑)"""
        # 간단한 키워드 매핑 (확장 가능)
        keyword_map = {
            "출장": "business trip",
            "공항": "airport",
            "박람회": "exhibition booth",
            "연수": "corporate training",
            "호텔": "hotel room",
            "비행기": "airplane flight",
            "여권": "passport travel",
            "와이파이": "wifi travel",
            "환전": "currency exchange",
            "짐": "packing luggage",
        }
        for ko, en in keyword_map.items():
            if ko in text:
                return en
        return "business travel"
