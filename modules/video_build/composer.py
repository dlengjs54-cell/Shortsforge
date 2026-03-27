"""
FFmpeg video assembly v5 - OOM-safe + guaranteed subtitles
"""

__version__ = "5.0.0"

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
    print(f"   [{stage}] {cs[:250]}")
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
    wrapped = _wrap(text)
    path.write_text(wrapped, encoding="utf-8")
    return wrapped


def _dt(tf, font, fs, position="center"):
    if not font or not tf.exists():
        return ""
    t = str(tf).replace(":", "\\:")
    f = font.replace(":", "\\:")
    if position == "bottom":
        ypos = "y=h-text_h-80"
    else:
        ypos = "y=(h-text_h)/2"
    return ":".join([
        f"drawtext=textfile='{t}'",
        f"fontfile='{f}'",
        f"fontsize={fs}",
        "fontcolor=white",
        "borderw=2",
        "bordercolor=black",
        "x=(w-text_w)/2",
        ypos,
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
    script = json.load(
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

    # === SUBTITLE MAP LOG ===
    print(f"   === SUBTITLE MAP ===")
    for i, seg in enumerate(segs):
        tx = seg.get("text", "")
        lb = seg["label"]
        has = "YES" if tx else "EMPTY"
        preview = tx[:40] if tx else "(none)"
        print(f"   [sub-map] s{i:02d} [{lb}] {has}: {preview}")

    # === STEP 1: pre-downscale ===
    print(f"   === STEP 1: pre-downscale ===")
    ds_map = {}
    for idx, cp in enumerate(clips):
        dur_c, cw, ch = _probe(cp)
        print(f"   {cp.name}: {cw}x{ch} {dur_c:.1f}s")
        ds = tmp / f"ds_{idx:02d}.mp4"
        vf_ds = (
            f"scale={w}:{h}"
            f":force_original_aspect_ratio=increase"
            f",crop={w}:{h}"
        )
        _run([
            "ffmpeg", "-y", "-i", str(cp),
            "-vf", vf_ds,
            "-r", str(fps),
            "-c:v", "libx264",
            *FF_MEM,
            "-pix_fmt", "yuv420p",
            "-an", str(ds),
        ], stage=f"ds-{idx:02d}", timeout=120)
        if ds.exists():
            ds_map[idx] = ds
            kb = ds.stat().st_size // 1024
            print(f"   ds_{idx:02d}.mp4 OK {kb}KB")

    # === STEP 2: segments with guaranteed subtitles ===
    print(f"   === STEP 2: segments ===")
    outs = []
    for i, seg in enumerate(segs):
        sd = seg["end"] - seg["start"]
        tx = seg.get("text", "")
        lb = seg["label"]

        # Write subtitle text file
        tf = tmp / f"sub_{i:02d}.txt"
        if tx:
            wrapped = _write_txt(tx, tf)
            print(f"   [sub] s{i:02d}: wrote {tf.name} = '{wrapped[:30]}...'")
        else:
            print(f"   [sub] s{i:02d}: NO TEXT for [{lb}]")

        # Find matching clip
        cp_match = _find_clip(i, lb, clips)
        op = tmp / f"s{i:02d}.mp4"

        # Get downscaled version
        ds = None
        if cp_match:
            ci = clips.index(cp_match) if cp_match in clips else -1
            if ci >= 0:
                ds = ds_map.get(ci)

        if ds and ds.exists():
            dd = _probe(ds)[0]
            dt_filter = _dt(tf, font, fs) if tx else ""

            print(f"   [{lb}] clip={ds.name} dur={dd:.1f} sub={'YES' if dt_filter else 'NO'}")

            if dd > 0 and dd < sd:
                _seg_pad(ds, op, sd, dd, w, h,
                         fps, dt_filter)
            else:
                _seg_trim(ds, op, sd, fps, dt_filter)
        else:
            dt_filter = _dt(tf, font, fs) if tx else ""
            print(f"   [{lb}] color bg sub={'YES' if dt_filter else 'NO'}")
            _seg_bg(op, sd, w, h, fps, dt_filter)

        if not op.exists():
            raise RuntimeError(f"seg {i} fail")
        kb = op.stat().st_size // 1024
        print(f"   s{i:02d}.mp4 OK {kb}KB sub={'applied' if tx else 'none'}")
        outs.append(op)

    # === STEP 3: concat ===
    print(f"   === STEP 3: concat {len(outs)} segs ===")
    cv = tmp / "c.mp4"
    _concat(outs, cv)

    # === STEP 4: mux audio ===
    print(f"   === STEP 4: mux audio ===")
    _mux(cv, project.audio_path,
         project.final_video_path, tdur)

    # === STEP 5: thumbnail ===
    print(f"   === STEP 5: thumbnail ===")
    try:
        from modules.video_build.thumbnail import generate_thumbnail
        generate_thumbnail(
            video_path=project.final_video_path,
            output_path=project.dir / "thumbnail.jpg",
            title=script.get("title", ""),
            hook=script.get("hook", ""),
            font=font,
        )
    except Exception as te:
        print(f"   WARN: thumbnail failed: {te}")

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


def _seg_trim(ds, op, d, fps, dt_filter):
    vf = dt_filter if dt_filter else None
    cmd = [
        "ffmpeg", "-y", "-i", str(ds),
        "-t", str(d),
    ]
    if vf:
        cmd += ["-vf", vf]
    cmd += [
        "-r", str(fps),
        "-c:v", "libx264", *FF_MEM,
        "-pix_fmt", "yuv420p",
        "-an", str(op),
    ]
    _run(cmd, stage=f"trim-{op.stem}", timeout=90)


def _seg_pad(ds, op, td, cd, w, h, fps, dt_filter):
    pad = td - cd
    vf = f"tpad=stop_mode=clone:stop_duration={pad:.2f}"
    if dt_filter:
        vf += "," + dt_filter
    _run([
        "ffmpeg", "-y", "-i", str(ds),
        "-vf", vf,
        "-t", str(td),
        "-r", str(fps),
        "-c:v", "libx264", *FF_MEM,
        "-pix_fmt", "yuv420p",
        "-an", str(op),
    ], stage=f"pad-{op.stem}", timeout=90)


def _seg_bg(op, d, w, h, fps, dt_filter):
    src = f"color=c=0x141420:s={w}x{h}:d={d}:r={fps}"
    if dt_filter:
        _run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", src,
            "-vf", dt_filter,
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
