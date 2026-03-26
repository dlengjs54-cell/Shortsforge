"""
개별 클립 처리
- 9:16 리사이즈/크롭
- 길이 조절
"""

from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip
from pathlib import Path


def process_clip(
    clip_path: Path,
    target_width: int = 1080,
    target_height: int = 1920,
    target_duration: float = None,
) -> VideoFileClip:
    """
    클립을 9:16 세로형으로 리사이즈/크롭
    - 가로형 → 중앙 크롭
    - 세로형 → 비율 유지 리사이즈
    - 길이 조절
    """
    clip = VideoFileClip(str(clip_path))

    # 길이 제한
    if target_duration and clip.duration > target_duration:
        clip = clip.subclip(0, target_duration)

    # 현재 비율 확인
    w, h = clip.size
    target_ratio = target_width / target_height  # 0.5625

    if w / h > target_ratio:
        # 가로가 더 넓음 → 높이 기준 리사이즈 후 좌우 크롭
        scale = target_height / h
        clip = clip.resize(height=target_height)
        # 중앙 크롭
        new_w = clip.size[0]
        x_center = new_w / 2
        x1 = int(x_center - target_width / 2)
        clip = clip.crop(x1=x1, y1=0, x2=x1 + target_width, y2=target_height)
    else:
        # 세로가 더 길거나 같음 → 너비 기준 리사이즈 후 상하 크롭
        scale = target_width / w
        clip = clip.resize(width=target_width)
        new_h = clip.size[1]
        y_center = new_h / 2
        y1 = int(y_center - target_height / 2)
        clip = clip.crop(x1=0, y1=y1, x2=target_width, y2=y1 + target_height)

    return clip


def create_color_clip(
    duration: float,
    color: tuple = (20, 20, 30),
    width: int = 1080,
    height: int = 1920,
) -> ColorClip:
    """빈 색상 클립 생성 (미디어 부족 시 폴백)"""
    return ColorClip(
        size=(width, height),
        color=color,
        duration=duration,
    )
