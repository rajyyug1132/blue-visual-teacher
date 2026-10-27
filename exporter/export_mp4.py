"""Frames -> MP4: Playwright drives renderer/player.html, FFmpeg encodes from image2pipe (AYUSH_BLUEPRINT 3).

    render_and_mux_mp4(artifact_dir, lang, progress_cb=None, fps=20) -> Path

Reads manifest.json + lesson_audio.wav from artifact_dir and writes lesson.mp4 next to them. Every request the page
makes is audited: anything that is not file:, data:, blob: or localhost fails the export (the offline proof).
"""
import base64
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAYER = ROOT / "renderer" / "player.html"
LOCAL_PREFIXES = ("file://", "data:", "blob:", "about:", "http://127.0.0.1", "http://localhost")
CHROMIUM_ARGS = ["--disable-gpu-vsync", "--font-render-hinting=none", "--force-color-profile=srgb"]


class OfflineViolation(RuntimeError):
    """The renderer tried to reach the network."""


def _ffmpeg_cmd(fps: int, audio: Path, out: Path) -> list[str]:
    return ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-vcodec", "mjpeg", "-framerate", str(fps),
            "-i", "-", "-i", str(audio),
            # JPEG frames are full-range (yuvj420p); convert to TV range so the file is plain yuv420p everywhere.
            "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "ultrafast",
            "-crf", "22", "-pix_fmt", "yuv420p", "-color_range", "tv",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)]


def render_and_mux_mp4(artifact_dir: Path, lang: str, progress_cb=None, fps: int = 20,
                       player: Path = PLAYER) -> Path:
    from playwright.sync_api import sync_playwright

    artifact_dir = Path(artifact_dir)
    manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
    audio = artifact_dir / manifest.get("audio", "lesson_audio.wav")
    out = artifact_dir / "lesson.mp4"
    tmp = artifact_dir / "lesson.partial.mp4"
    total = float(manifest.get("total_sec") or manifest["scenes"][-1]["end_sec"])
    frames = math.ceil(total * fps)
    blocked: list[str] = []

    proc = subprocess.Popen(_ffmpeg_cmd(fps, audio, tmp), stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=CHROMIUM_ARGS)
            page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
            page.on("request", lambda r: None if r.url.startswith(LOCAL_PREFIXES) else blocked.append(r.url))
            page.goto(Path(player).resolve().as_uri(), wait_until="load")
            page.evaluate("([t, s, l]) => window.initLesson(t, s, l)", [manifest["title"], manifest["scenes"], lang])
            page.wait_for_function("window.ready === true", timeout=30_000)
            for i in range(frames):
                # toDataURL skips the compositor: 2-3x faster than page.screenshot.
                data = page.evaluate(f"window.renderAtTime({i / fps:.4f}); "
                                     "document.getElementById('stage').toDataURL('image/jpeg', 0.9)")
                proc.stdin.write(base64.b64decode(data.split(",", 1)[1]))
                if progress_cb and i % 20 == 0:
                    progress_cb("render", int(i * 100 / frames))
            browser.close()
        if blocked:
            raise OfflineViolation(f"renderer made non-local requests: {blocked[:5]}")
        if progress_cb:
            progress_cb("encode", 0)
        proc.stdin.close()
        _, err = proc.communicate(timeout=600)
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg failed: " + err.decode("utf-8", "ignore")[-800:])
    except BaseException:
        proc.kill()
        tmp.unlink(missing_ok=True)  # never leave a broken or zero-byte MP4 behind
        raise
    tmp.replace(out)
    if progress_cb:
        progress_cb("encode", 100)
    return out


def export_from_manifest(html_path, timing_manifest, lesson_title, audio_wav_path, output_mp4_path,
                         progress_callback=None):
    """BLUEPRINT 5.1 signature, kept so run_pipeline.py and older callers keep working."""
    out = Path(output_mp4_path)
    manifest = {"title": lesson_title, "scenes": timing_manifest, "total_sec": timing_manifest[-1]["end_sec"],
                "audio": Path(audio_wav_path).name}
    (out.parent / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    cb = (lambda stage, pct: progress_callback(pct)) if progress_callback else None
    result = render_and_mux_mp4(out.parent, None, cb, player=Path(html_path))
    if result != out:
        result.replace(out)
    return out


def probe(mp4: Path) -> dict:
    """ffprobe summary used by the tests and the harness: codecs, pixel format, duration, size."""
    raw = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,pix_fmt:format=duration",
                          "-of", "json", str(mp4)], capture_output=True, text=True, check=True).stdout
    info = json.loads(raw)
    streams = {s["codec_type"]: s for s in info["streams"]}
    return {"video": streams.get("video", {}).get("codec_name"), "pix_fmt": streams.get("video", {}).get("pix_fmt"),
            "audio": streams.get("audio", {}).get("codec_name"), "duration": float(info["format"]["duration"]),
            "kb": Path(mp4).stat().st_size / 1024}
