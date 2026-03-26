"""
텍스트 오버레이
- 키워드 강조 스타일 텍스트 렌더링
- 화면 중앙/하단 배치
- 외곽선(stroke) 포함 가독성 확보
"""

from moviepy.editor import TextClip, CompositeVideoClip, VideoClip
from pathlib import Path


def create_text_overlay(
    text: str,
    duration: float,
    video_size: tuple = (1080, 1920),
    font_path: str = None,
    font_size: int = 48,
    text_color: str = "#FFFFFF",
    stroke_color: str = "#000000",
    stroke_width: int = 2,
    position: str = "center",
    margin_bottom: int = 300,
) -> TextClip:
    """
    텍스트 오버레이 클립 생성
    
    Args:
        text: 표시할 텍스트
        duration: 표시 시간(초)
        position: "center" | "bottom"
    """
    width, height = video_size

    # 텍스트 줄바꿈 처리 (너무 긴 경우)
    text = _auto_wrap(text, max_chars_per_line=16)

    # TextClip 생성
    txt_clip = TextClip(
        text,
        fontsize=font_size,
        font=font_path or "NotoSansKR-Bold",
        color=text_color,
        stroke_color=stroke_color,
        stroke_width=stroke_width,
        method="caption",
        size=(width - 120, None),  # 좌우 여백 60px씩
        align="center",
    )
    txt_clip = txt_clip.set_duration(duration)

    # 위치 설정
    if position == "bottom":
        txt_clip = txt_clip.set_position(("center", height - margin_bottom))
    else:  # center
        txt_clip = txt_clip.set_position("center")

    return txt_clip


def create_title_overlay(
    title: str,
    duration: float,
    video_size: tuple = (1080, 1920),
    font_path: str = None,
    font_size: int = 64,
) -> TextClip:
    """영상 제목용 큰 텍스트 (hook 구간에 사용)"""
    width, height = video_size
    title = _auto_wrap(title, max_chars_per_line=12)

    txt_clip = TextClip(
        title,
        fontsize=font_size,
        font=font_path or "NotoSansKR-Bold",
        color="#FFFFFF",
        stroke_color="#000000",
        stroke_width=3,
        method="caption",
        size=(width - 100, None),
        align="center",
    )
    txt_clip = txt_clip.set_duration(duration)
    txt_clip = txt_clip.set_position("center")

    return txt_clip


def _auto_wrap(text: str, max_chars_per_line: int = 16) -> str:
    """긴 텍스트를 적절히 줄바꿈"""
    if len(text) <= max_chars_per_line:
        return text

    words = text
    lines = []
    current_line = ""

    for char in words:
        current_line += char
        if len(current_line) >= max_chars_per_line and char in " ,.:!?을를이가은는도의에서":
            lines.append(current_line.strip())
            current_line = ""

    if current_line.strip():
        lines.append(current_line.strip())

    return "\n".join(lines) if lines else text
