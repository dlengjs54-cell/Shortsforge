"""
TTS Provider 추상 클래스
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    """음성 합성 인터페이스"""

    @abstractmethod
    def synthesize(self, text: str, output_path: Path) -> float:
        """
        텍스트 → 음성 파일 변환
        Returns: 생성된 오디오 길이(초)
        """
        pass

    def synthesize_from_script(
        self,
        script_path: Path,
        audio_path: Path,
        meta_path: Path,
    ):
        """
        script.json을 읽어 전체 나레이션 생성 + 타임스탬프 메타 생성
        """
        with open(script_path, "r", encoding="utf-8") as f:
            script = json.load(f)

        # 전체 텍스트 조합: hook → body → cta
        segments = []
        segments.append({"label": "hook", "text": script["hook"]})
        for item in script["body"]:
            segments.append({
                "label": f"body_{item['order']}",
                "text": item["text"],
            })
        segments.append({"label": "cta", "text": script["cta"]})

        full_text = " ".join(seg["text"] for seg in segments)

        # 음성 합성
        total_duration = self.synthesize(full_text, audio_path)
        print(f"   🔊 오디오 생성: {audio_path.name} ({total_duration:.1f}초)")

        # 타임스탬프 추정 (글자 수 비율 기반)
        total_chars = sum(len(seg["text"]) for seg in segments)
        current_time = 0.0
        meta_segments = []

        for seg in segments:
            char_ratio = len(seg["text"]) / total_chars
            duration = total_duration * char_ratio
            meta_segments.append({
                "label": seg["label"],
                "text": seg["text"],
                "start": round(current_time, 2),
                "end": round(current_time + duration, 2),
            })
            current_time += duration

        meta = {
            "total_duration_sec": round(total_duration, 2),
            "segments": meta_segments,
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        print(f"   📊 타임스탬프: {meta_path.name} ({len(meta_segments)}개 구간)")
