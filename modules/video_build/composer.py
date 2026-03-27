"""
FFmpeg 기반 영상 조립 (저메모리, ImageMagick 불필요)
"""

import json
import subprocess
import traceback
from pathlib import Path
from core.config_loader import Config
from core.project_manager import Project

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"


def _run_ffmpeg(cmd, timeout=180):
    print(f"   > {' '.join(cmd[:6])}...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        print(f"   FFmpeg STDERR: {result.stderr[-500:]}")
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-200:]}")
    return result


def compose(project: Project, config: Config):
    try:
        _compose_inner(project, config)
    except Exception as e:
        print(f"VIDEO BUILD ERROR: {e}")
        traceback.print_exc()
        raise


def _compose_inner(project: Project, config: Config):
    print("   FFmpeg video build start...")

    with open(project.audio_meta_path, "r", encoding="utf-8") as f:
        audio_meta = json.load(f)
    with open(project.script_path, "r", encoding="utf-8") as f:
        script = json.load(f)
    with open(project.media_manifest_path, "r", encoding="utf-8") as f:
        media_manifest = json.load(f)

    segments = audio_meta["segments"]
    total_duration = audio_meta["total_duration_sec"]
    w = config.get("video", "width", default=1080)
    h = config.get("video", "height", default=1920)
    fps = config.get("video", "fps", default=30)
    font_size = config.get("style", "font_size", default=44)

    font = FONT_PATH if Path(FONT_PATH).exists() else ""
    if not font:
        print("   WARN: font not found, text disabled")
    else:
        print(f"   Font OK: {font}")

    available_clips = sorted(project.media_dir.glob("*.mp4"))
    temp_dir = project.dir / "_temp"
    temp_dir.mkdir(exist_ok=True)

    segment_files = []

    for i, seg in enumerate(segments):
        dur = seg["end"] - seg["start"]
        text = seg.get("text", "")
        label = seg["label"]
        print(f"   [{label}] {dur:.1f}s - {text[:30]}...")

        clip_path = _find_clip(i, label, available_clips)
        seg_out = temp_dir / f"seg_{i:02d}.mp4"

        if clip_path and clip_path.exists():
            print(f"   clip: {clip_path.name}")
            _seg_from_clip(clip_path, seg_out, dur, w, h, fps, text, font, font_size)
        else:
            print(f"   clip: color bg")
            _seg_from_color(seg_out, dur, w, h, fps, text, font, font_size)

        if not seg_out.exists():
            raise RuntimeError(f"Segment {i} failed")
        print(f"   seg_{i:02d}.mp4 OK ({seg_out.stat().st_size // 1024}KB)")
        segment_files.append(seg_out)

    print(f"   Concat {len(segment_files)} segments...")
    concat_mp4 = temp_dir / "concat.mp4"
    _concat(segment_files, concat_mp4)

    print(f"   Add audio...")
    _add_audio(concat_mp4, project.audio_path, project.final_video_path, total_duration)

    for f in temp_dir.glob("*"):
        f.unlink()
    temp_dir.rmdir()

    if project.final_video_path.exists():
        mb = project.final_video_path.stat().st_size / (1024 * 1024)
        print(f"   DONE: {project.final_video_path.name} ({mb:.1f}MB)")
    else:
        raise RuntimeError("Final video not created")


def _find_clip(index, label, clips):
    m = {"hook": "clip_hook", "cta": "clip_cta"}
    target = m.get(label, f"clip_{index:02d}")
    for c in clips:
        if target in c.stem:
            return c
    if label.startswith("body_"):
        n = label.split("_")[1]
        for c in clips:
            if f"clip_{int(n):02d}" in c.stem:
                return c
    return clips[index] if index < len(clips) else None


def _escape(text):
    t = text.replace("\\", "\\\\\\\\")
    t = t.replace("'", "'\\\\\\''")
    t = t.replace(":", "\\\\:")
    t = t.replace("%", "%%%%")
    t = t.replace("[", "\\\\[")
    t = t.replace("]", "\\\\]")
    t = t.replace(";", "\\\\;")
    t = t.replace("\n", "\\n")
    return t


def _wrap_text(text, max_chars=18):
    if len(text) <= max_chars:
        return text
    result = []
    line = ""
    for ch in text:
        line += ch
        if len(line) >= max_chars and ch in " ,.:!?):":
            result.append(line.strip())
            line = ""
    if line.strip():
        result.append(line.strip())
    return "\n".join(result) if result else text


def _drawtext(text, font, font_size, dur):
    if not text or not font:
        return ""
    wrapped = _wrap_text(text)
    escaped = _escape(wrapped)
    return (
        f",drawtext=fontfile='{font}'"
        f":text='{escaped}'"
        f":fontsize={font_size}"
        f":fontcolor=white"
        f":borderw=3:bordercolor=black"
        f":x=(w-text_w)/2:y=(h-text_h)/2"
        f":line_spacing=10"
        f":box=1:boxcolor=black@0.4:boxborderw=15"
    )


def _seg_from_clip(clip, output, dur, w, h, fps, text, font, fs):
    vf = f"scale={w}:{h}:force_original_aspect_ratio=inc
