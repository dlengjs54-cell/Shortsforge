"""
FFmpeg 기반 영상 조립 (저메모리)
moviepy/ImageMagick 없이 FFmpeg만 사용
"""

import json
import subprocess
import os
from pathlib import Path
from core.config_loader import Config
from core.project_manager import Project


def compose(project: Project, config: Config):
    print("   🎬 FFmpeg 영상 조립 시작...")

    with open(project.audio_meta_path, "r", encoding="utf-8") as f:
        audio_meta = json.load(f)
    with open(project.script_path, "r", encoding="utf-8") as f:
        script = json.load(f)
    with open(project.media_manifest_path, "r", encoding="utf-8") as f:
        media_manifest = json.load(f)

    segments = audio_meta["segments"]
    total_duration = audio_meta["total_duration_sec"]
    v_width = config.get("video", "width", default=1080)
    v_height = config.get("video", "height", default=1920)
    fps = config.get("video", "fps", default=30)
    font_path = config.get("style", "font_path", default="./assets/fonts/NotoSansKR-Bold.ttf")
    font_size = config.get("style", "font_size", default=48)

    available_clips = sorted(project.media_dir.glob("*.mp4"))
    temp_dir = project.dir / "_temp"
    temp_dir.mkdir(exist_ok=True)

    segment_files = []

    for i, seg in enumerate(segments):
        seg_duration = seg["end"] - seg["start"]
        text = seg.get("text", "")
        print(f"   📹 [{seg['label']}] {seg_duration:.1f}s")

        clip_path = _find_clip(i, seg["label"], available_clips)
        seg_output = temp_dir / f"seg_{i:02d}.mp4"

        if clip_path and clip_path.exists():
            _make_segment_from_clip(
                clip_path, seg_output, seg_duration,
                v_width, v_height, fps, text, font_path, font_size
            )
        else:
            _make_segment_from_color(
                seg_output, seg_duration,
                v_width, v_height, fps, text, font_path, font_size
            )
        segment_files.append(seg_output)

    print(f"   🔗 {len(segment_files)}개 세그먼트 연결...")
    concat_video = temp_dir / "concat.mp4"
    _concat_segments(segment_files, concat_video)

    print(f"   🔊 오디오 합성...")
    _add_audio(concat_video, project.audio_path, project.final_video_path, total_duration)

    # 임시 파일 정리
    for f in temp_dir.glob("*"):
        f.unlink()
    temp_dir.rmdir()

    if project.final_video_path.exists():
        size_mb = project.final_video_path.stat().st_size / (1024 * 1024)
        print(f"   ✅ 완료: {project.final_video_path.name} ({size_mb:.1f}MB)")
    else:
        raise RuntimeError("영상 생성 실패")


def _find_clip(index, label, available_clips):
    label_map = {"hook": "clip_hook", "cta": "clip_cta"}
    target = label_map.get(label, f"clip_{index:02d}")
    for c in available_clips:
        if target in c.stem:
            return c
    if label.startswith("body_"):
        order = label.split("_")[1]
        for c in available_clips:
            if f"clip_{int(order):02d}" in c.stem:
                return c
    if index < len(available_clips):
        return available_clips[index]
    return None


def _escape_text(text):
    return text.replace("\\", "\\\\").replace("'", "\\'").replace(":","\\:").replace("%", "%%")


def _make_segment_from_clip(clip_path, output, duration, w, h, fps, text, font_path, font_size):
    escaped = _escape_text(text)
    font_abs = str(Path(font_path).resolve()) if Path(font_path).exists() else ""
    
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    if text and font_abs:
        vf += (
            f",drawtext=fontfile='{font_abs}'"
            f":text='{escaped}'"
            f":fontsize={font_size}"
            f":fontcolor=white"
            f":borderw=2:bordercolor=black"
            f":x=(w-text_w)/2:y=(h-text_h)/2"
        )

    cmd = [
        "ffmpeg", "-y", "-i", str(clip_path),
        "-t", str(duration),
        "-vf", vf,
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-an", str(output)
    ]
    subprocess.run(cmd, capture_output=True, timeout=120)


def _make_segment_from_color(output, duration, w, h, fps, text, font_path, font_size):
    escaped = _escape_text(text)
    font_abs = str(Path(font_path).resolve()) if Path(font_path).exists() else ""

    vf = f"color=c=0x141420:s={w}x{h}:d={duration}:r={fps}"
    if text and font_abs:
        vf += (
            f",drawtext=fontfile='{font_abs}'"
            f":text='{escaped}'"
            f":fontsize={font_size}"
            f":fontcolor=white"
            f":borderw=2:bordercolor=black"
            f":x=(w-text_w)/2:y=(h-text_h)/2"
        )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        str(output)
    ]
    subprocess.run(cmd, capture_output=True, timeout=120)


def _concat_segments(segment_files, output):
    list_file = output.parent / "concat_list.txt"
    with open(list_file, "w") as f:
        for seg in segment_files:
            f.write(f"file '{seg}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output)
    ]
    subprocess.run(cmd, capture_output=True, timeout=120)
    list_file.unlink()


def _add_audio(video_path, audio_path, output, duration):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-t", str(duration),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        str(output)
    ]
    subprocess.run(cmd, capture_output=True, timeout=180)

