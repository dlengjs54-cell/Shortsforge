"""
FFmpeg video assembly v3
- drawtext via textfile (not inline)
- Full error logging
- Short clip padding
"""

__version__ = "3.0.0"

import json
import os
import subprocess
import traceback
import hashlib
from pathlib import Path
from core.config_loader import Config
from core.project_manager import Project

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
]


def _log_version():
    me = Path(__file__).resolve()
    try:
        h = hashlib.md5(me.read_bytes()).hexdigest()[:8]
    except Exception:
        h = "?"
    print(f"   composer v{__version__} md5={h}")


def _find_font(config):
    cp = config.get("style", "font_path", default="")
    if cp and Path(cp).exists():
        print(f"   Font[cfg]: {cp}")
        return str(cp)
    ad = Path("assets/fonts")
    if ad.exists():
        for e in ("*.ttf", "*.otf", "*.ttc"):
            fl = list(ad.glob(e))
            if fl:
                print(f"   Font[assets]: {fl[0]}")
                return str(fl[0])
    for fp in FONT_CANDIDATES:
        if Path(fp).exists():
            print(f"   Font[sys]: {fp}")
            return fp
    print("   WARN: no font found")
    return ""


def _run(cmd, stage="?", timeout=180):
    cs = " ".join(str(c) for c in cmd)
    print(f"   [{stage}] {cs[:150]}...")
    try:
        r = subprocess.run(
            cmd, capture_output=True,
            text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"[{stage}] timeout {timeout}s")
    if r.returncode != 0:
        err = r.stderr[-600:] if r.stderr else "no stderr"
        print(f"   [{stage}] FAIL rc={r.returncode}")
        print(f"   {err}")
        raise RuntimeError(f"[{stage}] rc={r.returncode}")
    return r


def _probe_dur(p):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             str(p)],
            capture_output=True, text=True, timeout=10,
        )
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def _wrap(t, n=18):
    if len(t) <= n:
        return t
    lines = []
    ln = ""
    for c in t:
        ln += c
        if len(ln) >= n and c in " ,.:!?)":
            lines.append(ln.strip())
            ln = ""
    if ln.strip():
        lines.append(ln.strip())
    return "\n".join(lines) if lines else t


def _write_txt(text, path):
    path.write_text(_wrap(text, 18), encoding="utf-8")
    return path


def _dt_filter(txtfile, font, fs):
    if not font or not txtfile.exists():
        return ""
    tf = str(txtfile).replace("\\", "/")
    tf = tf.replace(":", "\\:")
    fn = font.replace(":", "\\:")
    parts = [
        f"drawtext=textfile='{tf}'",
        f"fontfile='{fn}'",
        f"fontsize={fs}",
        "fontcolor=white",
        "borderw=3",
        "bordercolor=black",
        "x=(w-text_w)/2",
        "y=(h-text_h)/2",
        "line_spacing=10",
        "box=1",
        "boxcolor=black@0.4",
        "boxborderw=15",
    ]
    return ":".join(parts)


def compose(project, config):
    try:
        _inner(project, config)
    except Exception as e:
        print(f"   VIDEO ERROR: {e}")
        traceback.print_exc()
        raise


def _inner(project, config):
    _log_version()
    meta = json.load(
        open(project.audio_meta_path, encoding="utf-8")
    )
    json.load(
        open(project.script_path, encoding="utf-8")
    )
    json.load(
        open(project.media_manifest_path, encoding="utf-8")
    )
    segs = meta["segments"]
    tdur = meta["total_duration_sec"]
    w = config.get("video", "width", default=1080)
    h = config.get("video", "height", default=1920)
    fps = config.get("video", "fps", default=30)
    fs = config.get("style", "font_size", default=44)
    font = _find_font(config)
    clips = sorted(project.media_dir.glob("*.mp4"))
    tmp = project.dir / "_temp"
    tmp.mkdir(exist_ok=True)
    outs = []

    for i, seg in enumerate(segs):
        sd = seg["end"] - seg["start"]
        tx = seg.get("text", "")
        lb = seg["label"]
        print(f"   [{lb}] {sd:.1f}s")

        tf = tmp / f"t{i:02d}.txt"
        if tx:
            _write_txt(tx, tf)

        cp = _find_clip(i, lb, clips)
        op = tmp / f"s{i:02d}.mp4"

        if cp and cp.exists():
            cd = _probe_dur(cp)
            if cd > 0 and cd < sd:
                print(f"   clip short {cd:.1f}<{sd:.1f}")
                _seg_clip_pad(
                    cp, op, sd, cd,
                    w, h, fps, tf, font, fs,
                )
            else:
                _seg_clip(
                    cp, op, sd,
                    w, h, fps, tf, font, fs,
                )
        else:
            _seg_color(
                op, sd, w, h, fps, tf, font, fs,
            )

        if not op.exists():
            raise RuntimeError(f"seg {i} missing")
        kb = op.stat().st_size // 1024
        print(f"   s{i:02d}.mp4 OK {kb}KB")
        outs.append(op)

    print(f"   concat {len(outs)}...")
    cv = tmp / "c.mp4"
    _concat(outs, cv)

    print(f"   mux audio...")
    _mux(
        cv, project.audio_path,
        project.final_video_path, tdur,
    )

    for f in tmp.glob("*"):
        f.unlink()
    tmp.rmdir()

    if project.final_video_path.exists():
        mb = project.final_video_path.stat().st_size
        mb = mb / (1024 * 1024)
        print(f"   DONE {mb:.1f}MB")
    else:
        raise RuntimeError("no final output")


def _find_clip(i, lb, cl):
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
    if i < len(cl):
        return cl[i]
    return None


def _seg_clip(cp, op, d, w, h, fps, tf, font, fs):
    vf = (
        f"scale={w}:{h}"
        f":force_original_aspect_ratio=increase"
        f",crop={w}:{h}"
    )
    dt = _dt_filter(tf, font, fs)
    if dt:
        vf += "," + dt
    _run([
        "ffmpeg", "-y", "-i", str(cp),
        "-t", str(d), "-vf", vf,
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-an", str(op),
    ], stage=f"clip-{op.stem}", timeout=120)


def _seg_clip_pad(cp, op, td, cd, w, h, fps, tf, font, fs):
    pad = td - cd
    vf = (
        f"scale={w}:{h}"
        f":force_original_aspect_ratio=increase"
        f",crop={w}:{h}"
        f",tpad=stop_mode=clone"
        f":stop_duration={pad:.2f}"
    )
    dt = _dt_filter(tf, font, fs)
    if dt:
        vf += "," + dt
    _run([
        "ffmpeg", "-y", "-i", str(cp),
        "-vf", vf, "-t", str(td),
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-an", str(op),
    ], stage=f"pad-{op.stem}", timeout=120)


def _seg_color(op, d, w, h, fps, tf, font, fs):
    src = f"color=c=0x141420:s={w}x{h}:d={d}:r={fps}"
    dt = _dt_filter(tf, font, fs)
    if dt:
        _run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", src,
            "-vf", dt,
            "-t", str(d),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            str(op),
        ], stage=f"bg-{op.stem}", timeout=120)
    else:
        _run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", src,
            "-t", str(d),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            str(op),
        ], stage=f"bg-{op.stem}", timeout=120)


def _concat(files, op):
    lf = op.parent / "list.txt"
    with open(lf, "w") as f:
        for s in files:
            f.write(f"file '{s}'\n")
    _run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(lf),
        "-c", "copy", str(op),
    ], stage="concat", timeout=120)
    lf.unlink()


def _mux(vp, ap, op, d):
    _run([
        "ffmpeg", "-y",
        "-i", str(vp), "-i", str(ap),
        "-t", str(d),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", str(op),
    ], stage="mux", timeout=180)
