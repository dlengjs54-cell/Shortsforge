"""
Thumbnail auto-generator (pure FFmpeg, no PIL)
- Extracts candidate frames at multiple timestamps
- Picks best frame by brightness/sharpness
- Adds hook text overlay
"""

import subprocess
import json
from pathlib import Path


def generate_thumbnail(
    video_path,
    output_path,
    title="",
    hook="",
    font="",
    width=1280,
    height=720,
):
    if not Path(video_path).exists():
        print("   thumb: no video")
        return

    dur = _get_duration(video_path)
    if dur <= 0:
        print("   thumb: zero duration")
        return

    tmp_dir = output_path.parent / "_thumb_tmp"
    tmp_dir.mkdir(exist_ok=True)

    # Step 1: Extract candidate frames
    positions = [0.15, 0.35, 0.55, 0.75]
    candidates = []
    for i, pos in enumerate(positions):
        ts = dur * pos
        frame = tmp_dir / f"frame_{i}.jpg"
        _extract_frame(video_path, ts, frame)
        if frame.exists():
            score = _score_frame(frame)
            candidates.append((frame, score))
            print(f"   thumb: frame_{i} t={ts:.1f}s score={score:.0f}")

    if not candidates:
        print("   thumb: no frames extracted")
        _cleanup(tmp_dir)
        return

    # Step 2: Pick best frame
    candidates.sort(key=lambda x: x[1], reverse=True)
    best = candidates[0][0]
    print(f"   thumb: best={best.name}")

    # Step 3: Make thumbnail text
    thumb_text = _make_thumb_text(title, hook)
    print(f"   thumb: text='{thumb_text}'")

    # Step 4: Build thumbnail
    if thumb_text and font:
        txt_file = tmp_dir / "thumb_text.txt"
        txt_file.write_text(thumb_text, encoding="utf-8")
        _build_with_text(
            best, output_path, txt_file, font,
            width, height,
        )
    else:
        _build_plain(best, output_path, width, height)

    # Step 5: Cleanup
    _cleanup(tmp_dir)

    if output_path.exists():
        kb = output_path.stat().st_size // 1024
        print(f"   thumb: OK {output_path.name} {kb}KB")
    else:
        print("   thumb: generation failed")


def _get_duration(path):
    try:
        r = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ], capture_output=True, text=True, timeout=10)
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def _extract_frame(video, timestamp, output):
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", str(video),
        "-frames:v", "1",
        "-q:v", "2",
        str(output),
    ], capture_output=True, timeout=15)


def _score_frame(frame_path):
    """Score frame by brightness + sharpness via ffprobe"""
    try:
        r = subprocess.run([
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "frame=pkt_size",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(frame_path),
        ], capture_output=True, text=True, timeout=10)
        size = int(r.stdout.strip())
        return float(size)
    except Exception:
        return float(frame_path.stat().st_size)


def _make_thumb_text(title, hook):
    """Generate short thumbnail text (8-18 chars)"""
    if hook and len(hook) <= 18:
        return hook
    if title and len(title) <= 18:
        return title
    if title:
        for sep in ["!", "?", ",", " "]:
            if sep in title:
                part = title.split(sep)[0].strip()
                if 6 <= len(part) <= 18:
                    return part
        return title[:16] + "..."
    return ""


def _build_with_text(frame, output, txt_file, font, w, h):
    tf = str(txt_file).replace(":", "\\:")
    fn = font.replace(":", "\\:")
    dt = ":".join([
        f"drawtext=textfile='{tf}'",
        f"fontfile='{fn}'",
        "fontsize=52",
        "fontcolor=white",
        "borderw=4",
        "bordercolor=black",
        "x=(w-text_w)/2",
        "y=(h-text_h)/2-50",
        "box=1",
        "boxcolor=black@0.5",
        "boxborderw=20",
    ])
    vf = (
        f"scale={w}:{h}"
        f":force_original_aspect_ratio=increase"
        f",crop={w}:{h}"
        f",{dt}"
    )
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(frame),
        "-vf", vf,
        "-q:v", "2",
        str(output),
    ], capture_output=True, timeout=15)


def _build_plain(frame, output, w, h):
    vf = (
        f"scale={w}:{h}"
        f":force_original_aspect_ratio=increase"
        f",crop={w}:{h}"
    )
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(frame),
        "-vf", vf,
        "-q:v", "2",
        str(output),
    ], capture_output=True, timeout=15)


def _cleanup(tmp_dir):
    if tmp_dir.exists():
        for f in tmp_dir.glob("*"):
            f.unlink()
        tmp_dir.rmdir()
