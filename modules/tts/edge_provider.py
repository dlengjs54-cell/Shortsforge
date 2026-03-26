"""
Microsoft Edge TTS 기반 음성 합성
무료, API 키 불필요, 한국어 품질 양호
"""

import asyncio
import edge_tts
from pathlib import Path
from mutagen.mp3 import MP3
from modules.tts.base import TTSProvider
from core.config_loader import Config


class EdgeTTSProvider(TTSProvider):

    def __init__(self, config: Config):
        self.voice = config.get("tts", "voice_id", default="ko-KR-SunHiNeural")
        self.speed = config.get("tts", "speed", default="+10%")

    def synthesize(self, text: str, output_path: Path) -> float:
        """Edge TTS로 음성 생성"""
        print(f"   🔊 Edge TTS 합성 중... (voice: {self.voice})")

        async def _generate():
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.speed,
            )
            await communicate.save(str(output_path))

        # asyncio 이벤트 루프 실행
        asyncio.run(_generate())

        # 생성된 파일 길이 측정
        duration = self._get_duration(output_path)
        return duration

    @staticmethod
    def _get_duration(audio_path: Path) -> float:
        """MP3 파일 길이 측정"""
        audio = MP3(str(audio_path))
        return audio.info.length
