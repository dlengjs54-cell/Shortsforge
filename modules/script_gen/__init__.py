"""
스크립트 생성 모듈
config의 script.provider 값에 따라 적절한 Provider 반환
"""

from core.config_loader import Config
from modules.script_gen.base import ScriptProvider


def create_provider(config: Config) -> ScriptProvider:
    """설정 기반 스크립트 Provider 팩토리"""
    provider_name = config.get("script", "provider", default="claude")

    if provider_name == "claude":
        from modules.script_gen.claude_provider import ClaudeScriptProvider
        return ClaudeScriptProvider(config)
    elif provider_name == "gemini":
        from modules.script_gen.gemini_provider import GeminiScriptProvider
        return GeminiScriptProvider(config)
    else:
        raise ValueError(f"지원하지 않는 스크립트 provider: {provider_name}")
