"""MP4 Exporter module for Blue Visual Teacher.

Captures frames from renderer/player.html via Playwright and pipes them to
FFmpeg image2pipe with narration audio to produce synchronized MP4 videos.
Features offline network auditing and high-speed toDataURL frame capture.
"""

import os
import sys
import json
import math
import shutil
import base64
import urllib.parse
import subprocess
from pathlib import Path
from typing import Callable, Optional, List, Dict, Any

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent

# Module-level audit record for verification in tests
_LAST_NETWORK_AUDIT: List[str] = []

def get_last_network_audit() -> List[str]:
    """Returns the recorded non-local requests from the last export run."""
    return list(_LAST_NETWORK_AUDIT)

def get_ffmpeg_bin() -> str:
    """Finds ffmpeg binary in PATH, venv Scripts, or known installation directories."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    candidates = [
        Path(sys.prefix) / "Scripts" / "ffmpeg.exe",
        Path(sys.prefix) / "bin" / "ffmpeg",
        Path(r"C:\Users\ayush\Downloads\ffmpeg-9.0.2-essentials_build\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    raise FileNotFoundError("FFmpeg executable not found on PATH or in environment.")

def get_ffprobe_bin() -> str:
    """Finds ffprobe binary in PATH, venv Scripts, or known installation directories."""
    found = shutil.which("ffprobe")
    if found:
        return found
    candidates = [
        Path(sys.prefix) / "Scripts" / "ffprobe.exe",
        Path(sys.prefix) / "bin" / "ffprobe",
        Path(r"C:\Users\ayush\Downloads\ffmpeg-9.0.2-essentials_build\ffmpeg-9.0.2-essentials_build\bin\ffprobe.exe"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    raise FileNotFoundError("FFprobe executable not found on PATH or in environment.")

FALLBACK_TEST_PLAYER_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Blue Visual Teacher Test Player</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body, html { width: 1280px; height: 720px; overflow: hidden; background: #0b132b; font-family: sans-serif; }
    canvas { width: 1280px; height: 720px; display: block; }
  </style>
</head>
<body>
  <canvas id="stage" width="1280" height="720"></canvas>
  <script>
    window.lessonTitle = "";
    window.scenes = [];
    window.currentLang = "en";
    window.totalDuration = 10;
    window.ready = false;

    window.initLesson = function(title, scenes, lang) {
      window.lessonTitle = title || "Lesson";
      window.scenes = scenes || [];
      window.currentLang = lang || "en";
      if (scenes && scenes.length > 0) {
        window.totalDuration = scenes[scenes.length - 1].end_sec || 10;
      }
      window.ready = true;
      return Promise.resolve();
    };

    window.renderAtTime = function(t_sec) {
      const canvas = document.getElementById("stage");
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#0b132b";
      ctx.fillRect(0, 0, 1280, 720);

      // Title & Header
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 38px sans-serif";
      ctx.fillText(window.lessonTitle, 60, 80);

      // Current scene
      let activeScene = window.scenes.find(s => t_sec >= s.start_sec && t_sec <= s.end_sec) || window.scenes[0];
      if (activeScene) {
        ctx.fillStyle = "#48cae4";
        ctx.font = "28px sans-serif";
        ctx.fillText(`Scene ${activeScene.id}: ${activeScene.visual.type.toUpperCase()}`, 60, 140);

        // Visual labels
        const labels = activeScene.visual.params.labels || [];
        ctx.fillStyle = "#e0aaff";
        ctx.font = "26px monospace";
        labels.forEach((lbl, idx) => {
          ctx.fillText(`• ${lbl}`, 80, 200 + idx * 45);
        });

        // Visual steps
        const steps = activeScene.visual.params.steps || [];
        ctx.fillStyle = "#caf0f8";
        ctx.font = "22px sans-serif";
        steps.forEach((st, idx) => {
          ctx.fillText(`→ ${st}`, 650, 200 + idx * 45);
        });

        // Dynamic motion test
        const pulse = (Math.sin(t_sec * 3.14159) + 1) / 2;
        ctx.fillStyle = "#ffb703";
        ctx.fillRect(60, 520, 1160 * (t_sec / Math.max(1, window.totalDuration)), 8);

        // Captions bar
        ctx.fillStyle = "rgba(0, 0, 0, 0.75)";
        ctx.fillRect(40, 560, 1200, 110);
        ctx.fillStyle = "#ffffff";
        ctx.font = "24px sans-serif";
        ctx.fillText(activeScene.narration || "", 60, 620);
      }
    };
  </script>
</body>
</html>
"""

def render_and_mux_mp4(
    artifact_dir: Path | str,
    lang: str = "en",
    progress_cb: Optional[Callable[[str, int], None]] = None,
    fps: int = 20,
    html_path: Optional[Path] = None,
    fail_on_network: bool = True,
) -> Path:
    """Renders visual frames from player.html via Playwright and encodes them into MP4 with audio.

    Args:
        artifact_dir: Directory containing manifest.json and lesson_audio.wav.
        lang: Target language code (e.g., 'en', 'hi', 'kn').
        progress_cb: Callback function reporting (stage, pct).
        fps: Frames per second (default 20).
        html_path: Path to player.html (defaults to renderer/player.html or fallback).
        fail_on_network: Whether to raise if any non-local network request occurs.

    Returns:
        Path to the rendered and muxed lesson.mp4.
    """
    global _LAST_NETWORK_AUDIT
    _LAST_NETWORK_AUDIT = []

    artifact_path = Path(artifact_dir).resolve()
    manifest_file = artifact_path / "manifest.json"
    audio_file = artifact_path / "lesson_audio.wav"
    output_mp4 = artifact_path / "lesson.mp4"

    if not manifest_file.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_file}")
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio WAV not found: {audio_file}")

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    lesson_title = manifest_data.get("title", "Lesson")
    scenes = manifest_data.get("scenes", [])
    total_duration = float(manifest_data.get("total_sec", 0.0))
    if total_duration <= 0 and scenes:
        total_duration = float(scenes[-1].get("end_sec", 10.0))

    total_frames = math.ceil(total_duration * fps)
    if total_frames <= 0:
        raise ValueError(f"Invalid duration: {total_duration}s yields {total_frames} frames")

    # Locate player.html
    temp_fallback_html = None
    if html_path and Path(html_path).exists():
        target_html_path = Path(html_path).resolve()
    else:
        renderer_html = REPO_ROOT / "renderer" / "player.html"
        if renderer_html.exists():
            target_html_path = renderer_html.resolve()
        else:
            # Create a fallback test player in artifact_dir
            temp_fallback_html = artifact_path / "_test_player.html"
            temp_fallback_html.write_text(FALLBACK_TEST_PLAYER_HTML, encoding="utf-8")
            target_html_path = temp_fallback_html.resolve()

    ffmpeg_bin = get_ffmpeg_bin()
    ffmpeg_cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "image2pipe",
        "-vcodec", "mjpeg",
        "-r", str(fps),
        "-i", "-",
        "-i", str(audio_file),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "22",
        "-vf", "scale=in_range=full:out_range=limited,format=yuv420p",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_mp4),
    ]

    # Delete existing mp4 if present so we never leave stale file
    if output_mp4.exists():
        output_mp4.unlink()

    proc = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    non_local_violations = []

    def handle_request(req):
        url = req.url
        parsed = urllib.parse.urlparse(url)
        # Check allowed local schemes and hosts
        if parsed.scheme in ("file", "data", "blob"):
            return
        if parsed.scheme in ("http", "https") and parsed.hostname in ("127.0.0.1", "localhost", "::1"):
            return
        # Outbound network attempt
        _LAST_NETWORK_AUDIT.append(url)
        non_local_violations.append(url)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-gpu-vsync",
                    "--font-render-hinting=none",
                    "--force-color-profile=srgb",
                ],
            )
            page = browser.new_page(
                viewport={"width": 1280, "height": 720},
                device_scale_factor=1,
            )

            # Register network audit interceptor
            page.on("request", handle_request)

            page.goto(target_html_path.as_uri(), wait_until="load")
            page.evaluate("() => document.fonts.ready")

            # Initialize lesson
            page.evaluate(
                "([title, scs, l]) => window.initLesson(title, scs, l)",
                [lesson_title, scenes, lang],
            )

            # Wait for window.ready
            page.wait_for_function("() => window.ready === true", timeout=10000)

            # Render loop
            for frame_idx in range(total_frames):
                t_sec = frame_idx / fps
                page.evaluate(f"window.renderAtTime({t_sec:.4f})")

                # High-speed capture: toDataURL directly from the canvas
                data_url = page.evaluate("""() => {
                    const canvas = document.getElementById('stage') || document.querySelector('canvas');
                    if (canvas && typeof canvas.toDataURL === 'function') {
                        return canvas.toDataURL('image/jpeg', 0.90);
                    }
                    return null;
                }""")

                if data_url and data_url.startswith("data:image/"):
                    b64_str = data_url.split(",", 1)[1]
                    frame_bytes = base64.b64decode(b64_str)
                else:
                    # Fallback to Playwright screenshot
                    frame_bytes = page.screenshot(type="jpeg", quality=90)

                proc.stdin.write(frame_bytes)

                if progress_cb and (frame_idx % max(1, fps) == 0 or frame_idx == total_frames - 1):
                    pct = int((frame_idx / total_frames) * 100)
                    progress_cb("render", pct)

            browser.close()

        if progress_cb:
            progress_cb("encode", 90)

        proc.stdin.close()
        _, stderr_bytes = proc.communicate()
        stderr_text = stderr_bytes.decode("utf-8", errors="ignore")

        if proc.returncode != 0:
            if output_mp4.exists():
                output_mp4.unlink()
            raise RuntimeError(f"FFmpeg mux failed (code {proc.returncode}):\n{stderr_text[-1000:]}")

        if not output_mp4.exists() or output_mp4.stat().st_size == 0:
            if output_mp4.exists():
                output_mp4.unlink()
            raise RuntimeError(f"FFmpeg produced empty or missing MP4: {stderr_text[-1000:]}")

        # Check network audit violations
        if non_local_violations and fail_on_network:
            if output_mp4.exists():
                output_mp4.unlink()
            raise RuntimeError(
                f"Air-gap audit violation: Non-local outbound requests detected during export: {non_local_violations}"
            )

        if progress_cb:
            progress_cb("encode", 100)

    finally:
        # Cleanup fallback HTML if created
        if temp_fallback_html and temp_fallback_html.exists():
            try:
                temp_fallback_html.unlink()
            except Exception:
                pass
        if proc.poll() is None:
            proc.kill()

    return output_mp4
