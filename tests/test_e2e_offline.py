"""End-to-end offline integration tests for Blue Visual Teacher.

Enforces air-gap network blocking, validates MP4 rendering and muxing with FFmpeg,
audits network requests, and tests the FastAPI backend endpoints with TestClient.
"""

import sys
import json
import time
import shutil
import socket
import tempfile
import subprocess
from pathlib import Path

import pytest
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from exporter.export_mp4 import render_and_mux_mp4, get_last_network_audit, get_ffprobe_bin
from exporter.app import app

def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")

# 1. Air-gap network blocker fixture
@pytest.fixture(autouse=True)
def block_outbound_network(monkeypatch):
    """Monkeypatches socket.socket.connect to block any non-local connection."""
    orig_connect = socket.socket.connect

    def guarded_connect(sock_self, address):
        if isinstance(address, tuple) and len(address) >= 2:
            host = str(address[0]).lower()
            allowed_hosts = {"127.0.0.1", "localhost", "::1"}
            if host not in allowed_hosts and not host.startswith("127."):
                raise RuntimeError(f"AIR-GAP VIOLATION: Attempted outbound network connection to {host}")
        return orig_connect(sock_self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)


def generate_test_wav(wav_path: Path, duration_sec: float, sample_rate: int = 24000):
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * 440.0 * t)
    # fade in/out
    fade = int(sample_rate * 0.05)
    audio[:fade] *= np.linspace(0, 1, fade)
    audio[-fade:] *= np.linspace(1, 0, fade)
    sf.write(str(wav_path), audio.astype(np.float32), sample_rate)


def probe_mp4_file(mp4_path: Path) -> dict:
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


def test_exporter_render_and_mux_offline():
    """Validates Playwright -> FFmpeg export on a fake artifact with network blocked."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_artifact_"))
    try:
        duration_sec = 6.0  # 6 seconds gives > 150 KB MP4 at 1280x720
        wav_file = temp_dir / "lesson_audio.wav"
        manifest_file = temp_dir / "manifest.json"

        generate_test_wav(wav_file, duration_sec=duration_sec, sample_rate=24000)

        manifest_data = {
            "title": "Ohm's Law: Voltage, Current, and Resistance",
            "lang": "en",
            "total_sec": duration_sec,
            "audio": "lesson_audio.wav",
            "sample_rate": 24000,
            "scenes": [
                {
                    "id": 1,
                    "start_sec": 0.0,
                    "end_sec": 3.0,
                    "duration_sec": 3.0,
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
                    "start_sec": 3.0,
                    "end_sec": 6.0,
                    "duration_sec": 3.0,
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
        manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # Call exporter
        mp4_path = render_and_mux_mp4(temp_dir, lang="en", fps=20, fail_on_network=True)

        # 1. Assert file exists and > 150 KB
        assert mp4_path.exists(), "MP4 file was not created"
        size_bytes = mp4_path.stat().st_size
        assert size_bytes > 150_000, f"Expected MP4 > 150 KB, got {size_bytes} bytes"

        # 2. ffprobe checks: h264 + yuv420p + aac
        info = probe_mp4_file(mp4_path)
        streams = info.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        assert v_stream is not None, "Missing video stream"
        assert a_stream is not None, "Missing audio stream"
        assert v_stream.get("codec_name") == "h264", f"Expected h264, got {v_stream.get('codec_name')}"
        assert v_stream.get("pix_fmt") == "yuv420p", f"Expected yuv420p, got {v_stream.get('pix_fmt')}"
        assert a_stream.get("codec_name") == "aac", f"Expected aac, got {a_stream.get('codec_name')}"

        # 3. Video duration within +/- 0.2 s of manifest.total_sec
        actual_dur = float(info.get("format", {}).get("duration", 0.0))
        assert abs(actual_dur - duration_sec) <= 0.2, (
            f"Video duration {actual_dur}s drifted by > 0.2s from manifest {duration_sec}s"
        )

        # 4. Zero non-local requests recorded
        audit = get_last_network_audit()
        assert len(audit) == 0, f"Non-local outbound requests found: {audit}"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_api_generate_and_status_e2e():
    """Tests the full API flow: /api/languages, /api/health, POST /api/generate, polling, and MP4 GET."""
    with TestClient(app) as client:
        # Languages
        lang_resp = client.get("/api/languages")
        assert lang_resp.status_code == 200
        languages = lang_resp.json()
        assert "en" in languages

        # Health
        health_resp = client.get("/api/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert "ffmpeg" in health_data
        assert "chromium" in health_data

        # Root redirect
        root_resp = client.get("/", follow_redirects=False)
        assert root_resp.status_code in (302, 307)
        assert "/web/index.html" in root_resp.headers.get("location", "")

        # POST /api/generate
        gen_resp = client.post("/api/generate", json={
            "topic": "Ohm's Law",
            "lang": "en"
        })
        assert gen_resp.status_code == 200
        data = gen_resp.json()
        assert "job_id" in data
        job_id = data["job_id"]

        # Poll status until done or timeout (max 30s)
        start_poll = time.time()
        final_job = None
        while time.time() - start_poll < 30:
            st_resp = client.get(f"/api/status/{job_id}")
            assert st_resp.status_code == 200
            st_data = st_resp.json()
            if st_data.get("stage") == "done":
                final_job = st_data
                break
            if st_data.get("stage") == "error":
                pytest.fail(f"Job failed with error: {st_data.get('error')}")
            time.sleep(0.5)

        assert final_job is not None, "Job timed out before reaching 'done'"
        assert final_job["pct"] == 100
        assert final_job["mp4_url"] is not None

        # Fetch MP4 via static mount
        mp4_resp = client.get(final_job["mp4_url"])
        assert mp4_resp.status_code == 200
        assert len(mp4_resp.content) > 50_000


@pytest.mark.slow
def test_full_pipeline_real_multilingual():
    """Runs full real pipeline for Ohm's Law in en, hi, kn (marked slow)."""
    from exporter.app import pipeline
    if not pipeline or not hasattr(pipeline, "generate_lesson"):
        pytest.skip("Full real pipeline (orchestrator.pipeline) not yet wired by team")

    for lang in ["en", "hi", "kn"]:
        out_dir = pipeline.generate_lesson("Ohm's Law", lang)
        mp4 = out_dir / "lesson.mp4"
        assert mp4.exists()
        assert mp4.stat().st_size > 150_000
