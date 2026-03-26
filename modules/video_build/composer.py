"""
영상 조립 오케스트레이터
- audio_meta.json 타이밍에 맞춰 클립 배치
- 텍스트 오버레이 적용
- BGM 믹싱
- 최종 MP4 출력
"""

import json
from pathlib import Path

from moviepy.editor import (
    concatenate_videoclips,
    CompositeVideoClip,
    AudioFileClip,
)

from modules.video_build.clip_processor import process_clip, create_color_clip
from modules.video_build.text_overlay import create_text_overlay, create_title_overlay
from modules.video_build.audio_mixer import mix_audio
from core.config_loader import Config
from core.project_manager import Project


def compose(project: Project, config: Config):
    """
    전체 영상 조립
    
    1. audio_meta에서 세그먼트 타이밍 로드
    2. 각 세그먼트에 맞는 클립 배치 + 크롭
    3. 텍스트 오버레이
    4. BGM 믹싱
    5. 최종 인코딩
    """
    print("   🎬 영상 조립 시작...")

    # ── 1) 메타데이터 로드 ──
    with open(project.audio_meta_path, "r", encoding="utf-8") as f:
        audio_meta = json.load(f)

    with open(project.script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    with open(project.media_manifest_path, "r", encoding="utf-8") as f:
        media_manifest = json.load(f)

    segments = audio_meta["segments"]
    total_duration = audio_meta["total_duration_sec"]

    # 비디오 설정
    v_width = config.get("video", "width", default=1080)
    v_height = config.get("video", "height", default=1920)
    fps = config.get("video", "fps", default=30)
    video_size = (v_width, v_height)

    # 스타일 설정
    font_path = config.get("style", "font_path")
    font_size = config.get("style", "font_size", default=48)
    text_color = config.get("style", "text_color", default="#FFFFFF")
    stroke_color = config.get("style", "text_stroke_color", default="#000000")
    stroke_width = config.get("style", "text_stroke_width", default=2)
    text_position = config.get("style", "text_position", default="center")
    bgm_dir = Path(config.get("style", "bg_music_dir", default=""))
    bgm_volume = config.get("style", "bg_music_volume", default=0.08)
    transition_dur = config.get("style", "transition_duration", default=0.5)

    # ── 2) 클립 매핑 ──
    clip_files = {c["file"]: c for c in media_manifest.get("clips", [])}
    media_dir = project.media_dir

    # 사용 가능한 클립 목록 (파일명 순)
    available_clips = sorted(media_dir.glob("*.mp4"))

    # ── 3) 세그먼트별 영상 조립 ──
    video_segments = []

    for i, seg in enumerate(segments):
        seg_duration = seg["end"] - seg["start"]
        label = seg["label"]
        text = seg.get("text", "")

        print(f"   📹 [{label}] {seg_duration:.1f}초 - {text[:20]}...")

        # 매칭 클립 찾기
        clip_video = _find_clip_for_segment(
            label=label,
            index=i,
            available_clips=available_clips,
            target_duration=seg_duration,
            video_size=video_size,
        )

        # 텍스트 오버레이 생성
        if label == "hook":
            txt_clip = create_title_overlay(
                title=text,
                duration=seg_duration,
                video_size=video_size,
                font_path=font_path,
                font_size=64,
            )
        else:
            txt_clip = create_text_overlay(
                text=text,
                duration=seg_duration,
                video_size=video_size,
                font_path=font_path,
                font_size=font_size,
                text_color=text_color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                position=text_position,
            )

        # 클립 + 텍스트 합성
        composite = CompositeVideoClip(
            [clip_video, txt_clip],
            size=video_size,
        ).set_duration(seg_duration)

        video_segments.append(composite)

    # ── 4) 세그먼트 연결 ──
    print(f"   🔗 {len(video_segments)}개 세그먼트 연결 중...")

    if transition_dur > 0 and len(video_segments) > 1:
        # crossfade 전환
        final_video = concatenate_videoclips(
            video_segments,
            method="compose",
            padding=-transition_dur,
        )
    else:
        final_video = concatenate_videoclips(video_segments, method="compose")

    # ── 5) 오디오 믹싱 ──
    mixed_audio = mix_audio(
        narration_path=project.audio_path,
        bgm_dir=bgm_dir if bgm_dir.exists() else None,
        bgm_volume=bgm_volume,
    )

    # 영상 길이를 오디오에 맞추기
    final_video = final_video.set_duration(total_duration)
    final_video = final_video.set_audio(mixed_audio)

    # ── 6) 최종 인코딩 ──
    output_path = project.final_video_path
    print(f"   💾 인코딩: {output_path.name}")

    final_video.write_videofile(
        str(output_path),
        fps=fps,
        codec=config.get("video", "codec", default="libx264"),
        audio_codec="aac",
        preset="medium",
        threads=4,
        logger=None,  # moviepy 로그 억제
    )

    # 리소스 정리
    final_video.close()
    for seg in video_segments:
        seg.close()

    # 최종 검증
    _validate_output(output_path, config)

    print(f"   ✅ 영상 생성 완료: {output_path}")


def _find_clip_for_segment(
    label: str,
    index: int,
    available_clips: list,
    target_duration: float,
    video_size: tuple,
):
    """세그먼트에 맞는 클립 찾기 + 처리"""
    # 라벨 기반 매칭 시도
    label_map = {
        "hook": "clip_hook",
        "cta": "clip_cta",
    }
    target_name = label_map.get(label, f"clip_{index:02d}")

    # 매칭 클립 검색
    matched = None
    for clip_path in available_clips:
        if target_name in clip_path.stem:
            matched = clip_path
            break

    # body_N 패턴 매칭
    if not matched and label.startswith("body_"):
        order = label.split("_")[1]
        for clip_path in available_clips:
            if f"clip_{int(order):02d}" in clip_path.stem:
                matched = clip_path
                break

    # 폴백: 인덱스 기반
    if not matched and index < len(available_clips):
        matched = available_clips[index]

    # 클립 처리 또는 색상 폴백
    if matched and matched.exists():
        return process_clip(
            clip_path=matched,
            target_width=video_size[0],
            target_height=video_size[1],
            target_duration=target_duration,
        )
    else:
        print(f"   ⚠️  클립 없음 → 색상 배경 사용")
        return create_color_clip(
            duration=target_duration,
            width=video_size[0],
            height=video_size[1],
        )


def _validate_output(output_path: Path, config: Config):
    """최종 영상 검증"""
    from moviepy.editor import VideoFileClip

    clip = VideoFileClip(str(output_path))
    duration = clip.duration
    w, h = clip.size
    clip.close()

    max_dur = config.get("video", "max_duration_sec", default=58)

    if duration > 60:
        print(f"   ⚠️  경고: 영상 길이 {duration:.1f}초 → 60초 초과!")
    elif duration > max_dur:
        print(f"   ⚠️  주의: 영상 길이 {duration:.1f}초 (목표 {max_dur}초 이하)")

    print(f"   📐 해상도: {w}x{h}, 길이: {duration:.1f}초")
