"""
FFmpeg video assembly v4 - OOM-safe
512MB RAM Docker compatible
"""

__version__ = "4.0.0"

import json
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
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
]

FF_MEM = ["-threads", "1", "-preset", "ultrafast"]


def _log_ver():
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
    print("   WARN: no font")
    return ""


def _run(cmd, stage="?", timeout=180):
    cs = " ".join(str(c) for c in cmd)
    print(f"   [{stage}] {cs[:200]}")
    try:
        r = subprocess.run(
            cmd, capture_output=True,
            text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"[{stage}] timeout")
    if r.returncode != 0:
        err = r.stderr[-600:] if r.stderr else ""
        print(f"   [{stage}] FAIL rc={r.returncode}")
        print(f"   {err[-300:]}")
        raise RuntimeError(f"[{stage}] rc={r.returncode}")
    return r


def _probe(p):
    """Get duration and resolution"""
    try:
        r = subprocess.run([
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of", "json", str(p),
        ], capture_output=True, text=True, timeout=10)
        d = json.loads(r.stdout)
        dur = float(d.get("format", {}).get("duration", 0))
        s = d.get("streams", [{}])[0]
        w = int(s.get("width", 0))
        h = int(s.get("height", 0))
        return dur, w, h
    except Exception:
        return 0.0, 0, 0


def _wrap(t, n=16):
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
    path.write_text(_wrap(text), encoding="utf-8")


def _dt(tf, font, fs):
    if not font or not tf.exists():
        return ""
    t = str(tf).replace(":", "\\:")
    f = font.replace(":", "\\:")
    return ":".join([
        f"drawtext=textfile='{t}'",
        f"fontfile='{f}'",
        f"fontsize={fs}",
        "fontcolor=white",
        "borderw=2",
        "bordercolor=black",
        "x=(w-text_w)/2",
        "y=(h-text_h)/2",
        "line_spacing=8",
        "box=1",
        "boxcolor=black@0.4",
        "boxborderw=12",
    ])


def compose(project, config):
    try:
        _inner(project, config)
    except Exception as e:
        print(f"   VIDEO ERROR: {e}")
        traceback.print_exc()
        raise


def _inner(project, config):
    _log_ver()
    meta = json.load(
        open(project.audio_meta_path, encoding="utf-8"))
    json.load(
        open(project.script_path, encoding="utf-8"))
    json.load(
        open(project.media_manifest_path, encoding="utf-8"))

    segs = meta["segments"]
    tdur = meta["total_duration_sec"]
    w = config.get("video", "width", default=720)
    h = config.get("video", "height", default=1280)
    fps = config.get("video", "fps", default=24)
    fs = config.get("style", "font_size", default=36)
    font = _find_font(config)
    clips = sorted(project.media_dir.glob("*.mp4"))
    tmp = project.dir / "_temp"
    tmp.mkdir(exist_ok=True)

    # Step 1: Pre-downscale all clips
    print(f"   === STEP 1: pre-downscale ===")
    ds_clips = {}
    for cp in clips:
        dur, cw, ch = _probe(cp)
        print(f"   {cp.name}: {cw}x{ch} {dur:.1f}s")
        ds = tmp / f"ds_{cp.name}"
        _run([
            "ffmpeg", "-y", "-i", str(cp),
            "-vf", f"scale={w}:{h}:"
            f"force_original_aspect_ratio=increase,"
            f"crop={w}:{h}",
            "-r", str(fps),
            "-c:v", "libx264",
            *FF_MEM,
            "-pix_fmt", "yuv420p",
            "-an", str(ds),
        ], stage=f"ds-{cp.stem}", timeout=120)
        if ds.exists():
            ds_clips[cp.name] = ds
            kb = ds.stat().st_size // 1024
            print(f"   ds_{cp.name} OK {kb}KB")

    # Step 2: Build segments
    print(f"   === STEP 2: segments ===")
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
        ds = ds_clips.get(cp.name) if cp else None

        if ds and ds.exists():
            dd = _probe(ds)[0]
            if dd > 0 and dd < sd:
                print(f"   pad {dd:.1f}->{sd:.1f}")
                _seg_pad(ds, op, sd, dd,
                         w, h, fps, tf, font, fs)
            else:
                _seg_trim(ds, op, sd,
                          fps, tf, font, fs)
        else:
            _seg_bg(op, sd, w, h,
                    fps, tf, font, fs)

        if not op.exists():
            raise RuntimeError(f"seg {i} fail")
        kb = op.stat().st_size // 1024
        print(f"   s{i:02d}.mp4 OK {kb}KB")
        outs.append(op)

    # Step 3: Concat
    print(f"   === STEP 3: concat ===")
    cv = tmp / "c.mp4"
    _concat(outs, cv)

    # Step 4: Mux audio
    print(f"   === STEP 4: mux ===")
    _mux(cv, project.audio_path,
         project.final_video_path, tdur)

    # Cleanup
    for f in tmp.glob("*"):
        f.unlink()
    tmp.rmdir()

    if project.final_video_path.exists():
        mb = project.final_video_path.stat().st_size
        print(f"   DONE {mb // 1048576}MB")
    else:
        raise RuntimeError("no output")


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


def _seg_trim(ds, op, d, fps, tf, font, fs):
    """Already downscaled, just trim + text"""
    dt = _dt(tf, font, fs)
    if dt:
        _run([
            "ffmpeg", "-y", "-i", str(ds),
            "-t", str(d),
            "-vf", dt,
            "-r", str(fps),
            "-c:v", "libx264", *FF_MEM,
            "-pix_fmt", "yuv420p",
            "-an", str(op),
        ], stage=f"trim-{op.stem}", timeout=90)
    else:
        _run([
            "ffmpeg", "-y", "-i", str(ds),
            "-t", str(d),
            "-r", str(fps),
            "-c:v", "libx264", *FF_MEM,
            "-pix_fmt", "yuv420p",
            "-an", str(op),
        ], stage=f"trim-{op.stem}", timeout=90)


def _seg_pad(ds, op, td, cd, w, h, fps, tf, font, fs):
    """Short clip: freeze last frame"""
    pad = td - cd
    vf = f"tpad=stop_mode=clone:stop_duration={pad:.2f}"
    dt = _dt(tf, font, fs)
    if dt:
        vf += "," + dt
    _run([
        "ffmpeg", "-y", "-i", str(ds),
        "-vf", vf,
        "-t", str(td),
        "-r", str(fps),
        "-c:v", "libx264", *FF_MEM,
        "-pix_fmt", "yuv420p",
        "-an", str(op),
    ], stage=f"pad-{op.stem}", timeout=90)


def _seg_bg(op, d, w, h, fps, tf, font, fs):
    """Color background + text"""
    src = f"color=c=0x141420:s={w}x{h}:d={d}:r={fps}"
    dt = _dt(tf, font, fs)
    if dt:
        _run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", src,
            "-vf", dt,
            "-t", str(d),
            "-c:v", "libx264", *FF_MEM,
            "-pix_fmt", "yuv420p",
            str(op),
        ], stage=f"bg-{op.stem}", timeout=90)
    else:
        _run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", src,
            "-t", str(d),
            "-c:v", "libx264", *FF_MEM,
            "-pix_fmt", "yuv420p",
            str(op),
        ], stage=f"bg-{op.stem}", timeout=90)


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
    ], stage="concat", timeout=60)
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
    ], stage="mux", timeout=120)
