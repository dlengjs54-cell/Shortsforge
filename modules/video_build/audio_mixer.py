"""
오디오 믹서
- 나레이션(TTS) + 배경음악(BGM) 합성
- BGM 볼륨 자동 조절
- 페이드 인/아웃
"""

import random
from pathlib import Path
from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    concatenate_audioclips,
)


def mix_audio(
    narration_path: Path,
    bgm_dir: Path = None,
    bgm_volume: float = 0.08,
    fade_in: float = 1.0,
    fade_out: float = 2.0,
) -> CompositeAudioClip | AudioFileClip:
    """
    나레이션 + BGM 믹싱
    
    BGM이 없으면 나레이션만 반환
    BGM이 나레이션보다 짧으면 루프 처리
    """
    narration = AudioFileClip(str(narration_path))
    total_duration = narration.duration

    # BGM 없으면 나레이션만
    if not bgm_dir or not bgm_dir.exists():
        return narration

    bgm_files = list(bgm_dir.glob("*.mp3")) + list(bgm_dir.glob("*.wav"))
    if not bgm_files:
        return narration

    # 랜덤 BGM 선택
    bgm_path = random.choice(bgm_files)
    bgm = AudioFileClip(str(bgm_path))

    # BGM이 짧으면 루프
    if bgm.duration < total_duration:
        loops_needed = int(total_duration / bgm.duration) + 1
        bgm = concatenate_audioclips([bgm] * loops_needed)

    # BGM 길이 맞추기
    bgm = bgm.subclip(0, total_duration)

    # 볼륨 조절 + 페이드
    bgm = bgm.volumex(bgm_volume)
    if fade_in > 0:
        bgm = bgm.audio_fadein(fade_in)
    if fade_out > 0:
        bgm = bgm.audio_fadeout(fade_out)

    # 믹싱
    mixed = CompositeAudioClip([narration, bgm])
    print(f"   🎵 BGM 믹싱: {bgm_path.name} (볼륨 {bgm_volume})")

    return mixed
