"""
미디어 소스 모듈
config의 media.provider 값 + fallback 지원
"""

from core.config_loader import Config
from modules.media_source.base import MediaProvider


def create_provider(config: Config) -> MediaProvider:
    provider_name = config.get("media", "provider", default="pexels")

    if provider_name == "pexels":
        from modules.media_source.pexels_provider import PexelsMediaProvider
        return PexelsMediaProvider(config)
    elif provider_name == "local":
        from modules.media_source.local_provider import LocalMediaProvider
        return LocalMediaProvider(config)
    else:
        raise ValueError(f"지원하지 않는 미디어 provider: {provider_name}")
