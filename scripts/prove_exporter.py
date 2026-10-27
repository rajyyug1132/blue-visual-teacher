"""Proof script for exporter/export_mp4.py.

Generates a fake artifact (golden manifest + synthesized sine WAV),
renders and muxes to MP4 using Playwright + FFmpeg,
and verifies output with ffprobe and network audit.
"""

import sys
import json
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import soundfile as sf
from exporter.export_mp4 import render_and_mux_mp4, get_last_network_audit, get_ffprobe_bin

def generate_sine_wav(path: Path, duration_sec: float = 3.0, sample_rate: int = 24000, freq: float = 440.0):
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    # Generate 440 Hz sine wave with smooth envelope
    audio = 0.5 * np.sin(2 * np.pi * freq * t)
    # 50 ms fade in/out to prevent click
    fade_len = int(sample_rate * 0.05)
    fade_in = np.linspace(0, 1, fade_len)
    fade_out = np.linspace(1, 0, fade_len)
    audio[:fade_len] *= fade_in
    audio[-fade_len:] *= fade_out
    sf.write(str(path), audio.astype(np.float32), sample_rate)

def create_fake_artifact(artifact_dir: Path, duration_sec: float = 3.0):
    artifact_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Generate audio WAV
    audio_path = artifact_dir / "lesson_audio.wav"
    generate_sine_wav(audio_path, duration_sec=duration_sec, sample_rate=24000)

    # 2. Golden manifest structure (matching PLAN 4.3)
    manifest = {
        "title": "Ohm's Law: Voltage, Current, and Resistance",
        "lang": "en",
        "total_sec": duration_sec,
        "audio": "lesson_audio.wav",
        "sample_rate": 24000,
        "scenes": [
            {
                "id": 1,
                "start_sec": 0.0,
                "end_sec": duration_sec / 2,
                "duration_sec": duration_sec / 2,
                "narration": "Why does your phone charger get warm while fast charging?",
                "visual": {
                    "type": "title",
                    "params": {
                        "labels": ["Ohm's Law", "V = I × R"],
                        "steps": ["Everyday Electricity"]
                    }
                }
            },
            {
                "id": 2,
                "start_sec": duration_sec / 2,
                "end_sec": duration_sec,
                "duration_sec": duration_sec / 2,
                "narration": "Voltage pushes current against electrical resistance.",
                "visual": {
                    "type": "equation",
                    "params": {
                        "labels": ["V = I × R", "V: Volts", "I: Amps", "R: Ohms"],
                        "steps": ["Current equals Voltage divided by Resistance"]
                    }
                }
            }
        ]
    }
    
    manifest_path = artifact_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

def probe_mp4(mp4_path: Path) -> dict:
    ffprobe = get_ffprobe_bin()
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(mp4_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)

def main():
    print("=== Proving exporter/export_mp4.py on fake artifact ===")
    test_dir = REPO_ROOT / "exporter" / "_test_artifact"
    try:
        duration = 3.0  # 3 seconds @ 20 fps = 60 frames
        print(f"1. Creating fake artifact in {test_dir} (duration={duration}s)...")
        create_fake_artifact(test_dir, duration_sec=duration)

        def progress(stage, pct):
            print(f"   [{stage.upper()}] {pct}%")

        print("2. Running render_and_mux_mp4...")
        mp4_path = render_and_mux_mp4(test_dir, lang="en", progress_cb=progress, fps=20)
        print(f"3. Rendered MP4: {mp4_path} ({mp4_path.stat().st_size} bytes)")

        # Verify MP4 exists and has content
        assert mp4_path.exists(), "MP4 does not exist"
        assert mp4_path.stat().st_size > 50000, f"MP4 too small: {mp4_path.stat().st_size} bytes"

        # Verify streams with ffprobe
        info = probe_mp4(mp4_path)
        streams = info.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        assert v_stream is not None, "No video stream found"
        assert a_stream is not None, "No audio stream found"

        v_codec = v_stream.get("codec_name")
        pix_fmt = v_stream.get("pix_fmt")
        a_codec = a_stream.get("codec_name")
        v_width = v_stream.get("width")
        v_height = v_stream.get("height")
        dur = float(info.get("format", {}).get("duration", 0.0))

        print(f"   Video: {v_codec} ({pix_fmt}) {v_width}x{v_height}")
        print(f"   Audio: {a_codec} {a_stream.get('sample_rate')} Hz")
        print(f"   Duration: {dur:.2f} s (expected ~{duration:.2f} s)")

        assert v_codec == "h264", f"Expected h264, got {v_codec}"
        assert pix_fmt == "yuv420p", f"Expected yuv420p, got {pix_fmt}"
        assert a_codec == "aac", f"Expected aac, got {a_codec}"
        assert v_width == 1280 and v_height == 720, f"Expected 1280x720, got {v_width}x{v_height}"
        assert abs(dur - duration) <= 0.3, f"Duration mismatch: {dur} vs {duration}"

        # Verify network audit
        audit = get_last_network_audit()
        print(f"4. Network audit non-local requests: {len(audit)}")
        assert len(audit) == 0, f"Found non-local requests: {audit}"

        print("\n=== SUCCESS: exporter/export_mp4.py is fully proven! ===")
        return 0
    finally:
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
