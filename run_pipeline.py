"""Golden-path CLI: plan (fixture or LLM) -> synthesize_all_scenes -> render_and_mux_mp4.

    python run_pipeline.py                       # golden Ohm's Law fixture, English
    python run_pipeline.py --topic "Monsoon"     # live planner (Ollama), English

Uses localization/ and exporter/ when they are merged; until then, falls back to the stubs below,
which keep the BLUEPRINT signatures so swapping in the real modules needs no change here.
"""
import os

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import argparse
import json
import shutil
import subprocess
import time
import wave
from pathlib import Path

from orchestrator.cache import topic_slug
from orchestrator.schema import LessonPlan

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures" / "golden_ohms_law.json"
PLAYER_HTML = ROOT / "renderer" / "player.html"
ARTIFACT_DIR = ROOT / "cache" / "artifacts"

STUB_WORDS_PER_SEC = 2.3
TAIL_PAD_SEC = 0.35
SAMPLE_RATE = 24000


class StubTTSEngine:
    """Stand-in for localization.tts_engine.OfflineTTSEngine: silent audio sized by word count."""

    def synthesize_all_scenes(self, scenes: list, lang: str, out_wav_path: str) -> list[dict]:
        timing_manifest, cursor_sec, n_frames = [], 0.0, 0
        for s in scenes:
            dur = round(len(s.narration.split()) / STUB_WORDS_PER_SEC + TAIL_PAD_SEC, 3)
            timing_manifest.append({
                "id": s.id,
                "start_sec": round(cursor_sec, 3),
                "end_sec": round(cursor_sec + dur, 3),
                "duration_sec": dur,
                "narration": s.narration,
                "visual": s.visual.model_dump(),
            })
            cursor_sec += dur
            n_frames += int(dur * SAMPLE_RATE)
        with wave.open(str(out_wav_path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(b"\x00\x00" * n_frames)
        return timing_manifest


def stub_render_and_mux_mp4(html_path, timing_manifest, lesson_title, audio_wav_path, output_mp4_path,
                            progress_callback=None):
    """Stand-in for exporter.export_mp4.render_and_mux_mp4: solid-colour video muxed with the lesson audio."""
    if shutil.which("ffmpeg") is None:
        print("  [stub exporter] ffmpeg not on PATH; skipping MP4")
        return None
    total = timing_manifest[-1]["end_sec"]
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=0x0b1d3a:s=1280x720:r=20:d={total}",
        "-i", str(audio_wav_path),
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest",
        str(output_mp4_path),
    ], check=True)
    if progress_callback:
        progress_callback(100)
    return Path(output_mp4_path)


def load_stages():
    try:
        from localization.tts_engine import OfflineTTSEngine
        tts, tts_name = OfflineTTSEngine(), "localization.tts_engine"
    except ImportError as exc:
        tts, tts_name = StubTTSEngine(), f"STUB ({exc})"
    try:
        from exporter.export_mp4 import render_and_mux_mp4
        export, export_name = render_and_mux_mp4, "exporter.export_mp4"
    except ImportError as exc:
        export, export_name = stub_render_and_mux_mp4, f"STUB ({exc})"
    print(f"  tts:      {tts_name}\n  exporter: {export_name}")
    return tts, export


def run(topic: str | None, lang: str = "en") -> Path:
    timings = {}
    t = time.perf_counter()
    if topic:
        from orchestrator.planner import plan_lesson
        plan, telemetry = plan_lesson(topic)
        print(f"  planner:  {json.dumps(telemetry)}")
    else:
        plan = LessonPlan.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
        topic = "Ohm's Law"
    timings["plan"] = time.perf_counter() - t

    tts, export = load_stages()
    out_dir = ARTIFACT_DIR / f"{topic_slug(topic)}_{lang}"
    out_dir.mkdir(parents=True, exist_ok=True)
    wav_path = out_dir / "lesson_audio.wav"

    t = time.perf_counter()
    timing_manifest = tts.synthesize_all_scenes(plan.scenes, lang, str(wav_path))
    timings["tts"] = time.perf_counter() - t

    total_sec = timing_manifest[-1]["end_sec"]
    manifest = {
        "title": plan.title, "lang": lang, "total_sec": total_sec,
        "audio": wav_path.name, "sample_rate": SAMPLE_RATE, "scenes": timing_manifest,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    t = time.perf_counter()
    mp4 = export(PLAYER_HTML, timing_manifest, plan.title, wav_path, out_dir / "lesson.mp4")
    timings["export"] = time.perf_counter() - t

    in_window = "OK" if 30.0 <= total_sec <= 90.0 else "OUT OF 30-90s WINDOW"
    print(f"  total_sec: {total_sec} ({in_window})")
    print("  stage sec: " + ", ".join(f"{k}={v:.2f}" for k, v in timings.items()))
    print(f"  artifacts: {out_dir}" + (f"\n  mp4:       {mp4}" if mp4 else ""))
    return out_dir


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", help="plan this topic with the live LLM instead of using the golden fixture")
    ap.add_argument("--lang", default="en", help="only 'en' until localization/translator.py is merged")
    args = ap.parse_args()
    if args.lang != "en":
        ap.error("non-English needs localization/translator.py, which is not merged yet")
    run(args.topic, args.lang)
