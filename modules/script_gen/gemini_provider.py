"""
Google Gemini 기반 스크립트 생성
"""

import google.generativeai as genai
from pathlib import Path
from modules.script_gen.base import ScriptProvider
from core.config_loader import Config


class GeminiScriptProvider(ScriptProvider):

    def __init__(self, config: Config):
        self.config = config
        self.model_name = config.get("script", "model", default="gemini-2.0-flash")
        self.temperature = config.get("script", "temperature", default=0.8)
        self.prompt_path = (
            Path(__file__).parent / "prompts" / "shorts_prompt.txt"
        )

        # API 키 설정
        api_key = config.get_api_key("GEMINI_API_KEY")
        genai.configure(api_key=api_key)

    def generate(self, topic: str) -> dict:
        """Gemini로 쇼츠 대본 생성"""
        print(f"   🤖 Gemini ({self.model_name}) 스크립트 생성 중...")

        # 프롬프트 조합
        prompt = self.load_prompt(
            self.prompt_path,
            topic=topic,
            domain=self.config.get("script", "domain", default=""),
            brand_name=self.config.get("script", "brand_name", default=""),
        )

        # Gemini API 호출
        model = genai.GenerativeModel(
            self.model_name,
            generation_config=genai.GenerationConfig(
                temperature=self.temperature,
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(prompt)

        # JSON 파싱
        script_data = self.parse_json_response(response.text)

        # 기본 검증
        self._validate(script_data, topic)
        print(f"   📝 제목: {script_data.get('title', '(없음)')}")
        return script_data

    def _validate(self, data: dict, topic: str):
        """스크립트 구조 검증"""
        required = ["title", "hook", "body", "cta"]
        for key in required:
            if key not in data:
                raise ValueError(f"스크립트에 '{key}' 필드가 없습니다")

        if not isinstance(data["body"], list) or len(data["body"]) < 2:
            raise ValueError("body는 최소 2개 항목이 필요합니다")

        # 글자 수 경고
        total = len(data["hook"])
        for item in data["body"]:
            total += len(item.get("text", ""))
        total += len(data["cta"])

        max_chars = self.config.get("script", "max_chars", default=500)
        if total > max_chars:
            print(f"   ⚠️  글자 수 초과: {total}자 (제한 {max_chars}자) - 60초를 넘을 수 있습니다")
