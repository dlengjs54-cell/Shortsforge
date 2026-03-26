"""
스크립트 생성 Provider 추상 클래스
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path


class ScriptProvider(ABC):
    """스크립트 생성기 인터페이스"""

    @abstractmethod
    def generate(self, topic: str) -> dict:
        """
        주제를 받아 쇼츠 대본 생성
        Returns:
            dict: {title, hook, body[], cta, hashtags}
        """
        pass

    def save(self, script_data: dict, output_path: Path):
        """스크립트를 JSON 파일로 저장"""
        # 글자 수 / 예상 시간 자동 계산
        total_text = script_data.get("hook", "")
        for item in script_data.get("body", []):
            total_text += item.get("text", "")
        total_text += script_data.get("cta", "")

        script_data["_meta"] = {
            "total_chars": len(total_text),
            "estimated_duration_sec": round(len(total_text) / 8.5, 1),  # 한국어 ~8.5자/초
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, ensure_ascii=False, indent=2)

        chars = script_data["_meta"]["total_chars"]
        dur = script_data["_meta"]["estimated_duration_sec"]
        print(f"   📝 스크립트 저장: {output_path.name} ({chars}자, 약 {dur}초)")

    def load_prompt(self, prompt_path: Path, **kwargs) -> str:
        """프롬프트 템플릿 로드 + 변수 치환"""
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
        return template.format(**kwargs)

    @staticmethod
    def parse_json_response(text: str) -> dict:
        """AI 응답에서 JSON 추출 (마크다운 코드블록 처리)"""
        text = text.strip()
        # ```json ... ``` 블록 제거
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        return json.loads(text)
