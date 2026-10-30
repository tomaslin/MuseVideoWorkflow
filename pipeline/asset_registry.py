#!/usr/bin/env python3
"""MuseVideoWorkflow asset registry.

Problem this solves, stated plainly: generated clips used to exist only as
bare MP4 files. Nothing recorded their reference images, their timestamps,
their prompts, or anything a later reader could actually inspect without
playing the video back — which is exactly how "I can't see the video" and
"I can't hear the audio" excuses were born.

What this module stores for every registered asset, next to the project
(not in a separate tool's memory):

  * identity: asset id, shot id, kind, original filename, SHA-256, size,
    and the source file's own modification time (its generation timestamp
    as recorded on disk) plus the time it was registered here.
  * video facts from ffprobe: duration, dimensions, frame rate, video and
    audio codecs, audio sample rate and channel count.
  * video you can actually look at without playing it: still frames
    extracted at 0%, 25%, 50%, 75% and 100% of the duration, plus a
    contact sheet (one image, all five frames, each labelled with its
    timestamp). A later reader opens the contact sheet as an image and
    sees the shot. That is the "can see" part.
  * audio you can actually inspect without listening to it: a waveform
    image, a spectrogram image, and per-second RMS loudness (a list of
    {second, rms} pairs). That is the "can hear" part, as far as a
    waveform and loudness curve can take it.
  * speech, honestly: if a `whisper` command is installed, it is run and
    its transcript is stored. If it is not installed, the registry says
    so explicitly (transcription_available: false) instead of inventing
    words. A transcript file supplied by a human (--transcript-file) is
    stored verbatim and marked as human-supplied.
  * references: every reference image passed with --reference is COPIED
    into the asset folder (with its SHA-256 recorded), so the reference
    that shaped a clip survives with the clip instead of living only in
    some other folder, chat, or link.
  * edit timing: --edit-start / --edit-end record where this asset sits
    in an assembled edit, if known. The guide timing of a shot is not
    confused with the clip's own duration.

Layout per project:

    projects/<slug>/assets/<asset_id>/
        asset.json            # everything above, machine-readable
        frames/frame_000.jpg  # 5 stills, labelled by second in asset.json
        contact_sheet.jpg     # the 5 stills in one image
        waveform.png          # audio waveform (video/audio assets only)
        spectrogram.png       # audio spectrogram (best effort)
        audio.json            # per-second RMS + audio facts
        references/<file>     # copied reference images

    projects/<slug>/assets/index.json   # all assets, sorted by asset id
    projects/<slug>/assets/index.html   # human-browsable index: contact
                                        # sheets, waveforms, facts, links

The media file itself is NOT duplicated into the registry (binaries are
large and the integration cannot push them anyway). Its path, hash and
size are recorded, and `verify` re-checks the hash so a moved or replaced
file is caught instead of silently trusted.

Usage:
    python3 pipeline/asset_registry.py register <media> --project-dir projects/<slug> \
        --asset-id s01 --shot s01 --prompt-file prompts/s01.txt \
        --reference references/rafa.jpg --edit-start 0 --edit-end 8
    python3 pipeline/asset_registry.py scan <clips-dir> --project-dir projects/<slug>
    python3 pipeline/asset_registry.py index --project-dir projects/<slug>
    python3 pipeline/asset_registry.py describe --project-dir projects/<slug> --asset-id s01
    python3 pipeline/asset_registry.py verify --project-dir projects/<slug>

Only the standard library, ffmpeg/ffprobe, and (optionally) Pillow are
needed. If Pillow is absent, the contact sheet falls back to ffmpeg's
tile filter. If whisper is absent, transcription is honestly absent.
"""
import argparse
import array
import datetime
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys


def run(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {r.stderr.strip()[:500]}")
    return r


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iso(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat()


def ffprobe(path):
    out = run(["ffprobe", "-v", "error", "-show_entries",
               "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
               "-show_entries", "format=duration,size",
               "-of", "json", path]).stdout
    data = json.loads(out)
    video = next((s for s in data.get("streams", []) if s["codec_type"] == "video"), None)
    audio = next((s for s in data.get("streams", []) if s["codec_type"] == "audio"), None)
    facts = {"duration_sec": float(data["format"]["duration"]),
             "size_bytes": int(data["format"]["size"])}
    if video:
        facts.update({"width": video.get("width"), "height": video.get("height"),
                      "video_codec": video.get("codec_name"),
                      "frame_rate": video.get("r_frame_rate")})
    if audio:
        facts.update({"audio_codec": audio.get("codec_name"),
                      "sample_rate": int(audio["sample_rate"]) if audio.get("sample_rate") else None,
                      "channels": audio.get("channels")})
    return facts, bool(video), bool(audio)


def extract_frames(media, out_dir, duration):
    """Five stills at 0/25/50/75/100% of duration. Returns [{second, file}]."""
    os.makedirs(out_dir, exist_ok=True)
    fracs = [0.0, 0.25, 0.5, 0.75, 1.0]
    frames = []
    for i, frac in enumerate(fracs):
        sec = min(duration - 0.05, max(0.0, duration * frac)) if duration > 0.1 else 0.0
        name = f"frame_{i:03d}.jpg"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{sec:.3f}", "-i", media,
             "-frames:v", "1", "-q:v", "3", os.path.join(out_dir, name)])
        frames.append({"second": round(sec, 3), "file": f"frames/{name}"})
    return frames


def contact_sheet(frame_paths, out_path, duration):
    """One image with all frames, each labelled with its timestamp.

    frame_paths: list of {"path": ..., "label": ...}. Frames are portrait
    (720x1280), so they are laid out in a 2-column grid, not a single
    5-wide strip that becomes unreadable. If Pillow is unavailable, fall
    back to an ffmpeg hstack of the labelled inputs (still one image,
    still all frames — the earlier tile-filter fallback only ever filled
    the first cell, because tile consumes frames from one stream).
    """
    try:
        from PIL import Image, ImageDraw
        import math as _math
        thumbs = []
        for item in frame_paths:
            im = Image.open(item["path"])
            thumb_w = 360
            h = int(im.height * thumb_w / im.width)
            thumbs.append(im.resize((thumb_w, h)))
        cols = 2
        rows = _math.ceil(len(thumbs) / cols)
        cell_h = max(t.height for t in thumbs) + 28
        sheet = Image.new("RGB", (cols * 360, rows * cell_h), "black")
        draw = ImageDraw.Draw(sheet)
        for i, (t, item) in enumerate(zip(thumbs, frame_paths)):
            x = (i % cols) * 360
            y = (i // cols) * cell_h
            sheet.paste(t, (x, y + 28))
            draw.text((x + 8, y + 6), item["label"], fill="white")
        sheet.save(out_path, quality=88)
        return True
    except Exception:
        pass
    try:
        inputs = []
        for item in frame_paths:
            inputs += ["-i", item["path"]]
        n = len(frame_paths)
        filt = "".join(f"[{i}:v]" for i in range(n)) + f"hstack=inputs={n}[v]"
        run(["ffmpeg", "-y", "-v", "error"] + inputs +
            ["-filter_complex", filt, "-map", "[v]", "-frames:v", "1", out_path])
        return True
    except Exception:
        return False


def audio_analysis(media, out_dir, duration):
    """Waveform + spectrogram images and per-second RMS. Returns dict."""
    os.makedirs(out_dir, exist_ok=True)
    result = {"waveform": None, "spectrogram": None, "rms_per_second": []}
    wave = os.path.join(out_dir, "waveform.png")
    r = run(["ffmpeg", "-y", "-v", "error", "-i", media,
             "-filter_complex", "showwavespic=s=1200x240", "-frames:v", "1", wave],
            check=False)
    if r.returncode == 0 and os.path.exists(wave):
        result["waveform"] = "waveform.png"
    spec = os.path.join(out_dir, "spectrogram.png")
    r = run(["ffmpeg", "-y", "-v", "error", "-i", media,
             "-filter_complex", "showspectrumpic=s=1200x240", "-frames:v", "1", spec],
            check=False)
    if r.returncode == 0 and os.path.exists(spec):
        result["spectrogram"] = "spectrogram.png"
    # Per-second RMS via a decoded mono 16-bit raw stream, stdlib only.
    try:
        proc = subprocess.run(["ffmpeg", "-v", "error", "-i", media, "-ac", "1",
                               "-ar", "16000", "-f", "s16le", "-"],
                              capture_output=True, check=True)
        samples = array.array("h")
        samples.frombytes(proc.stdout)
        if sys.byteorder == "big":
            samples.byteswap()
        sr = 16000
        for sec in range(int(math.ceil(duration))):
            chunk = samples[sec * sr:(sec + 1) * sr]
            if not chunk:
                break
            rms = math.sqrt(sum(x * x for x in chunk) / len(chunk)) / 32768.0
            result["rms_per_second"].append({"second": sec, "rms": round(rms, 4)})
    except Exception as e:
        result["rms_error"] = str(e)[:200]
    return result


def transcribe(media, out_dir):
    """Whisper if installed, else an explicit absence. Never invented."""
    if shutil.which("whisper") is None:
        return {"available": False, "engine": None,
                "note": "whisper is not installed; no transcript was generated. "
                        "Supply one with --transcript-file to store it verbatim."}
    try:
        run(["whisper", media, "--model", "tiny", "--output_format", "txt",
             "--output_dir", out_dir], check=True)
        txt = None
        for name in os.listdir(out_dir):
            if name.endswith(".txt"):
                with open(os.path.join(out_dir, name)) as f:
                    txt = f.read()
        return {"available": True, "engine": "whisper tiny", "text": txt}
    except Exception as e:
        return {"available": False, "engine": "whisper",
                "note": f"whisper run failed: {e}"[:300]}


def register(args):
    media = args.media
    if not os.path.exists(media):
        raise SystemExit(f"media file not found: {media}")
    project_dir = args.project_dir
    asset_id = args.asset_id or os.path.splitext(os.path.basename(media))[0]
    asset_dir = os.path.join(project_dir, "assets", asset_id)
    os.makedirs(asset_dir, exist_ok=True)
    facts, has_video, has_audio = ffprobe(media)
    duration = facts["duration_sec"]
    asset = {
        "asset_id": asset_id,
        "shot": args.shot,
        "kind": args.kind or ("video" if has_video else "audio" if has_audio else "file"),
        "source_file": os.path.basename(media),
        "source_path": os.path.relpath(media, project_dir)
        if os.path.abspath(media).startswith(os.path.abspath(project_dir)) else media,
        "sha256": sha256_of(media),
        "size_bytes": facts["size_bytes"],
        "source_mtime_utc": iso(os.path.getmtime(media)),
        "registered_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "facts": facts,
        "has_video": has_video,
        "has_audio": has_audio,
        "frames": [],
        "contact_sheet": None,
        "audio": None,
        "transcription": None,
        "references": [],
        "edit_start_sec": args.edit_start,
        "edit_end_sec": args.edit_end,
        "prompt": None,
        "notes": args.notes,
    }
    if args.prompt_file:
        with open(args.prompt_file) as f:
            asset["prompt"] = f.read()
    elif args.prompt:
        asset["prompt"] = args.prompt
    if has_video:
        frames = extract_frames(media, os.path.join(asset_dir, "frames"), duration)
        asset["frames"] = frames
        frame_paths = [{"path": os.path.join(asset_dir, f["file"]),
                        "label": f"{f['second']}s"} for f in frames]
        if contact_sheet(frame_paths, os.path.join(asset_dir, "contact_sheet.jpg"), duration):
            asset["contact_sheet"] = "contact_sheet.jpg"
    if has_audio:
        asset["audio"] = audio_analysis(media, asset_dir, duration)
    if args.transcript_file:
        with open(args.transcript_file) as f:
            asset["transcription"] = {"available": True, "engine": "human-supplied",
                                      "text": f.read()}
    elif has_audio:
        asset["transcription"] = transcribe(media, asset_dir)
    for ref in args.reference or []:
        if not os.path.exists(ref):
            print(f"warning: reference not found, skipped: {ref}", file=sys.stderr)
            continue
        dest_dir = os.path.join(asset_dir, "references")
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, os.path.basename(ref))
        shutil.copyfile(ref, dest)
        asset["references"].append({
            "file": f"references/{os.path.basename(ref)}",
            "original_path": ref,
            "sha256": sha256_of(dest),
            "size_bytes": os.path.getsize(dest),
        })
    with open(os.path.join(asset_dir, "asset.json"), "w") as f:
        json.dump(asset, f, indent=2)
    rebuild_index(project_dir)
    print(json.dumps({"asset_id": asset_id, "asset_dir": asset_dir,
                      "duration_sec": duration, "sha256": asset["sha256"],
                      "frames": len(asset["frames"]),
                      "contact_sheet": asset["contact_sheet"],
                      "references": len(asset["references"]),
                      "transcription_available":
                          bool(asset["transcription"] and asset["transcription"].get("available"))},
                     indent=2))
    return asset


def rebuild_index(project_dir):
    assets_root = os.path.join(project_dir, "assets")
    assets = []
    if os.path.isdir(assets_root):
        for name in sorted(os.listdir(assets_root)):
            p = os.path.join(assets_root, name, "asset.json")
            if os.path.isfile(p):
                with open(p) as f:
                    assets.append(json.load(f))
    assets.sort(key=lambda a: a["asset_id"])
    with open(os.path.join(assets_root, "index.json"), "w") as f:
        json.dump({"project_dir": project_dir,
                   "rebuilt_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "asset_count": len(assets), "assets": assets}, f, indent=2)
    # Human-browsable index: contact sheets and waveforms are the point.
    parts = ["<html><head><meta charset='utf-8'><title>Asset index</title>"
             "<style>body{font-family:sans-serif;max-width:900px;margin:2em auto}"
             "img{max-width:100%}section{border-top:1px solid #ccc;padding:1em 0}</style>"
             "</head><body><h1>Asset index</h1>"
             "<p>Each asset keeps its frames, contact sheet, waveform, prompt, "
             "references and hashes here, so a later reader can inspect it "
             "without playing the original file.</p>"]
    for a in assets:
        base = a["asset_id"]
        parts.append(f"<section><h2>{base}</h2>"
                     f"<p>Shot: {a.get('shot')} · Kind: {a.get('kind')} · "
                     f"Duration: {a['facts'].get('duration_sec')}s · "
                     f"Size: {a.get('size_bytes')} bytes<br>"
                     f"Source: {a.get('source_file')} · "
                     f"SHA-256: {a.get('sha256')}<br>"
                     f"Source mtime: {a.get('source_mtime_utc')} · "
                     f"Registered: {a.get('registered_at_utc')}</p>")
        if a.get("contact_sheet"):
            parts.append(f"<p>Contact sheet (frames at 0/25/50/75/100%):<br>"
                         f"<img src='{base}/contact_sheet.jpg'></p>")
        if a.get("audio") and a["audio"].get("waveform"):
            parts.append(f"<p>Waveform:<br><img src='{base}/waveform.png'></p>")
        if a.get("prompt"):
            import html as _html
            parts.append(f"<pre>{_html.escape(a['prompt'][:2000])}</pre>")
        parts.append("</section>")
    parts.append("</body></html>")
    with open(os.path.join(assets_root, "index.html"), "w") as f:
        f.write("\n".join(parts))
    return assets


def cmd_scan(args):
    exts = {".mp4", ".mov", ".mkv", ".webm", ".mp3", ".wav", ".m4a", ".png", ".jpg", ".jpeg", ".webp"}
    done, skipped = [], []
    for name in sorted(os.listdir(args.dir)):
        if os.path.splitext(name)[1].lower() not in exts:
            continue
        asset_id = os.path.splitext(name)[0]
        if os.path.exists(os.path.join(args.project_dir, "assets", asset_id, "asset.json")):
            skipped.append(name)
            continue
        sub = argparse.Namespace(media=os.path.join(args.dir, name),
                                 project_dir=args.project_dir, asset_id=asset_id,
                                 shot=None, kind=None, prompt_file=None, prompt=None,
                                 reference=[], transcript_file=None,
                                 edit_start=None, edit_end=None, notes="registered by scan")
        register(sub)
        done.append(name)
    print(json.dumps({"registered": done, "already_registered": skipped}, indent=2))


def cmd_describe(args):
    p = os.path.join(args.project_dir, "assets", args.asset_id, "asset.json")
    with open(p) as f:
        a = json.load(f)
    print(f"{a['asset_id']} ({a['kind']}, shot {a.get('shot')})")
    print(f"  source: {a['source_file']}  sha256:{a['sha256'][:16]}…  {a['size_bytes']} bytes")
    print(f"  duration: {a['facts'].get('duration_sec')}s  "
          f"{a['facts'].get('width')}x{a['facts'].get('height')}  "
          f"video:{a['facts'].get('video_codec')} audio:{a['facts'].get('audio_codec')}")
    print(f"  source mtime: {a['source_mtime_utc']}  registered: {a['registered_at_utc']}")
    print(f"  frames: {', '.join(f['file'] + '@' + str(f['second']) + 's' for f in a['frames'])}")
    print(f"  contact sheet: {a.get('contact_sheet')}")
    if a.get("audio"):
        rms = a["audio"].get("rms_per_second", [])
        print(f"  audio RMS/second: {[r['rms'] for r in rms]}")
        print(f"  waveform: {a['audio'].get('waveform')} spectrogram: {a['audio'].get('spectrogram')}")
    t = a.get("transcription") or {}
    print(f"  transcription available: {t.get('available')} ({t.get('engine')})")
    print(f"  references: {[r['file'] for r in a['references']]}")
    if a.get("edit_start_sec") is not None:
        print(f"  edit timing: {a['edit_start_sec']}s – {a['edit_end_sec']}s")
    if a.get("prompt"):
        print(f"  prompt: {a['prompt'][:300]}")


def cmd_verify(args):
    assets = rebuild_index(args.project_dir)
    problems = []
    for a in assets:
        src = a["source_path"]
        full = src if os.path.isabs(src) else os.path.join(args.project_dir, src)
        if not os.path.exists(full):
            problems.append(f"{a['asset_id']}: source missing: {src}")
        elif sha256_of(full) != a["sha256"]:
            problems.append(f"{a['asset_id']}: hash mismatch (file changed since registration)")
        for ref in a["references"]:
            rp = os.path.join(args.project_dir, "assets", a["asset_id"], ref["file"])
            if not os.path.exists(rp) or sha256_of(rp) != ref["sha256"]:
                problems.append(f"{a['asset_id']}: reference missing/changed: {ref['file']}")
    print(json.dumps({"assets": len(assets), "problems": problems}, indent=2))
    return 1 if problems else 0


def main():
    ap = argparse.ArgumentParser(description="MuseVideoWorkflow asset registry")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register")
    r.add_argument("media")
    r.add_argument("--project-dir", required=True)
    r.add_argument("--asset-id")
    r.add_argument("--shot")
    r.add_argument("--kind")
    r.add_argument("--prompt-file")
    r.add_argument("--prompt")
    r.add_argument("--reference", action="append", default=[])
    r.add_argument("--transcript-file")
    r.add_argument("--edit-start", type=float)
    r.add_argument("--edit-end", type=float)
    r.add_argument("--notes")
    s = sub.add_parser("scan")
    s.add_argument("dir")
    s.add_argument("--project-dir", required=True)
    i = sub.add_parser("index")
    i.add_argument("--project-dir", required=True)
    d = sub.add_parser("describe")
    d.add_argument("--project-dir", required=True)
    d.add_argument("--asset-id", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--project-dir", required=True)
    args = ap.parse_args()
    if args.cmd == "register":
        register(args)
    elif args.cmd == "scan":
        cmd_scan(args)
    elif args.cmd == "index":
        assets = rebuild_index(args.project_dir)
        print(json.dumps({"assets": len(assets)}, indent=2))
    elif args.cmd == "describe":
        cmd_describe(args)
    elif args.cmd == "verify":
        sys.exit(cmd_verify(args))


if __name__ == "__main__":
    main()
