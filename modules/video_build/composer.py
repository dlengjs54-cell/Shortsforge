"""
FFmpeg 기반 영상 조립 (저메모리)
moviepy/ImageMagick 없이 FFmpeg만 사용
"""

import json
import subprocess
import traceback
from pathlib import Path
from core.config_loader import Config
from core.project_manager import Project


def _run_ffmpeg(cmd, timeout=180):
    """FFmpeg 실행 + 에러 로그 출력"""
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
    v_width = config.get("video", "width", default=1080)
    v_height = config.get("video", "height", default=1920)
    fps = config.get("video", "fps", default=30)
    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
    font_size = config.get("style", "font_size", default=44)

    available_clips = sorted(project.media_dir.glob("*.mp4"))
    temp_dir = project.dir / "_temp"
    temp_dir.mkdir(exist_ok=True)

    # Check font
    fp = Path(font_path)
    if not fp.exists():
        print(f"   WARN: font not found at {font_path}, trying fallback...")
        for candidate in [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/app/assets/fonts/NotoSansKR-Bold.ttf",
        ]:
            if Path(candidate).exists():
                font_path = candidate
                print(f"   Using font: {font_path}")
                break
        else:
            print("   WARN: No font found, text overlay disabled")
            font_path = ""

    segment_files = []

    for i, seg in enumerate(segments):
        seg_duration = seg["end"] - seg["start"]
        text = seg.get("text", "")
        label = seg["label"]
        print(f"   [{label}] {seg_duration:.1f}s - {text[:30]}...")

        clip_path = _find_clip(i, label, available_clips)
        seg_output = temp_dir / f"seg_{i:02d}.mp4"

        if clip_path and clip_path.exists():
            print(f"   Using clip: {clip_path.name}")
            _make_segment_from_clip(
                clip_path, seg_output, seg_duration,
                v_width, v_height, fps, text, font_path, font_size
            )
        else:
            print(f"   No clip, using color background")
            _make_segment_from_color(
                seg_output, seg_duration,
                v_width, v_height, fps, text, font_path, font_size
            )

        if not seg_output.exists():
            raise RuntimeError(f"Segment {i} creation failed")
        print(f"   seg_{i:02d}.mp4 OK ({seg_output.stat().st_size // 1024}KB)")
        segment_files.append(seg_output)

    print(f"   Concatenating {len(segment_files)} segments...")
    concat_video = temp_dir / "concat.mp4"
    _concat_segments(segment_files, concat_video)

    if not concat_video.exists():
        raise RuntimeError("Concat failed")
    print(f"   concat.mp4 OK ({concat_video.stat().st_size // 1024}KB)")

    print(f"   Adding audio...")
    _add_audio(concat_video, project.audio_path, project.final_video_path, total_duration)

    # Cleanup
    for f in temp_dir.glob("*"):
        f.unlink()
    temp_dir.rmdir()

    if project.final_video_path.exists():
        size_mb = project.final_video_path.stat().st_size / (1024 * 1024)
        print(f"   DONE: {project.final_video_path.name} ({size_mb:.1f}MB)")
    else:
        raise RuntimeError("Final video not created")


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


def _escape_drawtext(text):
    """FFmpeg drawtext filter escaping"""
    text = text.replace("\\", "\\\\\\\\")
    text = text.replace("'", "'\\\\\\''")
    text = text.replace(":", "\\\\:")
    text = text.replace("%", "%%%%")
    text = text.replace("[", "\\\\[")
    text = text.replace("]", "\\\\]")
    text = text.replace(";", "\\\\;")
    return text


def _build_drawtext(text, font_path, font_size):
    """Build drawtext filter string"""
    if not text or not font_path:
        return ""
    escaped = _escape_drawtext(text)
    return (
        f",drawtext=fontfile='{font_path}'"
        f":text='{escaped}'"
        f":fontsize={font_size}"
        f":fontcolor=white"
        f":borderw=2:bordercolor=black"
        f":x=(w-text_w)/2:y=(h-text_h)/2"
        f":line_spacing=8"
    )


def _make_segment_from_clip(clip_path, output, duration, w, h, fps, text, font_path, font_size):
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    vf += _build_drawtext(text, font_path, font_size)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(clip_path),
        "-t", str(duration),
        "-vf", vf,
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output)
    ]
    _run_ffmpeg(cmd, timeout=120)


def _make_segment_from_color(output, duration, w, h, fps, text, font_path, font_size):
    vf_src = f"color=c=0x141420:s={w}x{h}:d={duration}:r={fps}"
    drawtext = _build_drawtext(text, font_path, font_size)

    if drawtext:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", vf_src,
            "-vf", drawtext.lstrip(","),
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            str(output)
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", vf_src,
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            str(output)
        ]
    _run_ffmpeg(cmd, timeout=120)


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
    _run_ffmpeg(cmd, timeout=120)
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
    _run_ffmpeg(cmd, timeout=180)

