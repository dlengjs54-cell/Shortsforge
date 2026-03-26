"""
TTS 모듈
config의 tts.provider 값에 따라 Provider 반환
"""

from core.config_loader import Config
from modules.tts.base import TTSProvider


def create_provider(config: Config) -> TTSProvider:
    provider_name = config.get("tts", "provider", default="edge")

    if provider_name == "edge":
        from modules.tts.edge_provider import EdgeTTSProvider
        return EdgeTTSProvider(config)
    # elif provider_name == "google":
    #     from modules.tts.google_provider import GoogleTTSProvider
    #     return GoogleTTSProvider(config)
    # elif provider_name == "elevenlabs":
    #     from modules.tts.elevenlabs_provider import ElevenLabsProvider
    #     return ElevenLabsProvider(config)
    else:
        raise ValueError(f"지원하지 않는 TTS provider: {provider_name}")
