import json
import subprocess
import traceback
from pathlib import Path
from core.config_loader import Config
from core.project_manager import Project

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"


def _ff(cmd, t=180):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=t)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-500:])
        raise RuntimeError(r.stderr[-200:])


def compose(project, config):
    try:
        _do(project, config)
    except Exception as e:
        print("VIDEO ERROR:", e)
        traceback.print_exc()
        raise


def _do(project, config):
    print("FFmpeg build...")
    meta = json.load(open(project.audio_meta_path, encoding="utf-8"))
    script = json.load(open(project.script_path, encoding="utf-8"))
    mmf = json.load(open(project.media_manifest_path, encoding="utf-8"))
    segs = meta["segments"]
    dur = meta["total_duration_sec"]
    w = config.get("video", "width", default=1080)
    h = config.get("video", "height", default=1920)
    fps = config.get("video", "fps", default=30)
    fs = config.get("style", "font_size", default=44)
    font = FONT if Path(FONT).exists() else ""
    if font:
        print("Font OK:", font)
    else:
        print("WARN: no font")
    clips = sorted(project.media_dir.glob("*.mp4"))
    td = project.dir / "_temp"
    td.mkdir(exist_ok=True)
    outs = []
    for i, s in enumerate(segs):
        d = s["end"] - s["start"]
        tx = s.get("text", "")
        lb = s["label"]
        print(f"  [{lb}] {d:.1f}s")
        cp = _fc(i, lb, clips)
        op = td / f"s{i:02d}.mp4"
        if cp and cp.exists():
            _sv(cp, op, d, w, h, fps, tx, font, fs)
        else:
            _sc(op, d, w, h, fps, tx, font, fs)
        if not op.exists():
            raise RuntimeError(f"seg {i} fail")
        print(f"  s{i:02d}.mp4 OK")
        outs.append(op)
    print("Concat...")
    cv = td / "c.mp4"
    _cat(outs, cv)
    print("Audio...")
    _aa(cv, project.audio_path, project.final_video_path, dur)
    for f in td.glob("*"):
        f.unlink()
    td.rmdir()
    if project.final_video_path.exists():
        mb = project.final_video_path.stat().st_size / 1048576
        print(f"DONE: {mb:.1f}MB")
    else:
        raise RuntimeError("no output")


def _fc(i, lb, cl):
    m = {"hook": "clip_hook", "cta": "clip_cta"}
    t = m.get(lb, f"clip_{i:02d}")
    for c in cl:
        if t in c.stem:
            return c
    if lb.startswith("body_"):
        n = lb.split("_")[1]
        for c in cl:
            if f"clip_{int(n):02d}" in c.stem:
                return c
    return cl[i] if i < len(cl) else None


def _esc(t):
    for old, new in [
        ("\\", "\\\\\\\\"),
        ("'", "'\\\\\\''"),
        (":", "\\\\:"),
        ("%", "%%%%"),
        ("[", "\\\\["),
        ("]", "\\\\]"),
        (";", "\\\\;"),
    ]:
        t = t.replace(old, new)
    return t


def _wrap(t, n=18):
    if len(t) <= n:
        return t
    r = []
    line = ""
    for c in t:
        line += c
        if len(line) >= n and c in " ,.:!?):":
            r.append(line.strip())
            line = ""
    if line.strip():
        r.append(line.strip())
    return "\\n".join(r) if r else t


def _dt(tx, font, fs):
    if not tx or not font:
        return ""
    e = _esc(_wrap(tx))
    dt = "drawtext="
    dt += f"fontfile='{font}':"
    dt += f"text='{e}':"
    dt += f"fontsize={fs}:"
    dt += "fontcolor=white:"
    dt += "borderw=3:bordercolor=black:"
    dt += "x=(w-text_w)/2:y=(h-text_h)/2:"
    dt += "line_spacing=10:"
    dt += "box=1:boxcolor=black@0.4:boxborderw=15"
    return dt


def _sv(cp, op, d, w, h, fps, tx, font, fs):
    vf = f"scale={w}:{h}"
    vf += ":force_original_aspect_ratio=increase"
    vf += f",crop={w}:{h}"
    dt = _dt(tx, font, fs)
    if dt:
        vf += "," + dt
    cmd = [
        "ffmpeg", "-y", "-i", str(cp),
        "-t", str(d), "-vf", vf,
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-an", str(op),
    ]
    _ff(cmd, 120)


def _sc(op, d, w, h, fps, tx, font, fs):
    src = f"color=c=0x141420:s={w}x{h}:d={d}:r={fps}"
    dt = _dt(tx, font, fs)
    if dt:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", src,
            "-vf", dt,
            "-t", str(d),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", str(op),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", src,
            "-t", str(d),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", str(op),
        ]
    _ff(cmd, 120)


def _cat(files, op):
    lf = op.parent / "l.txt"
    with open(lf, "w") as f:
        for s in files:
            f.write(f"file '{s}'\n")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(lf),
        "-c", "copy", str(op),
    ]
    _ff(cmd, 120)
    lf.unlink()


def _aa(vp, ap, op, d):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(vp), "-i", str(ap),
        "-t", str(d),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", str(op),
    ]
    _ff(cmd, 180)
