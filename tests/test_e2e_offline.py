"""End-to-end with the network blocked (AYUSH_BLUEPRINT 6).

The autouse fixture makes any outbound socket connect to a non-local host raise, inside this test process.
Chromium is audited separately by the exporter (any non-local request fails the export).
Slow, real-model run: set E2E_REAL=1 (needs Ollama + IndicTrans2 + Kokoro + MMS weights).
"""
import json
import math
import os
import shutil
import socket
import sys
import time
import uuid
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from orchestrator import pipeline  # noqa: E402
from orchestrator.schema import LessonPlan  # noqa: E402

FIXTURE = ROOT / "fixtures" / "golden_ohms_law.json"
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    real_connect = socket.socket.connect

    def guarded(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if host not in LOCAL_HOSTS:
            raise OSError(f"network blocked in tests: {address}")
        return real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")


def test_network_is_really_blocked():
    with pytest.raises(OSError, match="network blocked"):
        socket.create_connection(("1.1.1.1", 53), timeout=2)


class WordRateTTS:
    """Deterministic stand-in for OfflineTTSEngine: 2.3 words/s + 0.35 s tail, a quiet tone so AAC has content."""

    def synthesize_all_scenes(self, scenes, lang, out_wav_path):
        manifest, cursor, frames = [], 0.0, bytearray()
        for s in scenes:
            dur = round(len(s.narration.split()) / 2.3 + 0.35, 3)
            manifest.append({"id": s.id, "start_sec": round(cursor, 3), "end_sec": round(cursor + dur, 3),
                             "duration_sec": dur, "narration": s.narration, "visual": s.visual.model_dump()})
            n = int(dur * 24000)
            for i in range(n):
                v = int(10000 * math.sin(2 * math.pi * 220 * i / 24000)) if (i % 7200) < 3600 else 0
                frames += v.to_bytes(2, "little", signed=True)
            cursor += dur
        with wave.open(str(out_wav_path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(bytes(frames))
        return manifest


def golden_plan(topic=None):
    plan = LessonPlan.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    if topic:
        plan.title = topic
    return plan, {"fixture": True}


def require_exporter():
    pytest.importorskip("playwright.sync_api")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not on PATH")


def assert_mp4_ok(out: Path, total: float):
    from exporter.export_mp4 import probe
    info = probe(out / "lesson.mp4")
    assert info["kb"] > 150, info
    assert (info["video"], info["pix_fmt"], info["audio"]) == ("h264", "yuv420p", "aac"), info
    assert abs(info["duration"] - total) <= 0.2, info
    assert 30.0 <= total <= 90.0
    return info


def test_d7_golden_lesson_exports_offline(tmp_path):
    require_exporter()
    from exporter.export_mp4 import render_and_mux_mp4
    plan, _ = golden_plan()
    timing = WordRateTTS().synthesize_all_scenes(plan.scenes, "en", tmp_path / "lesson_audio.wav")
    total = timing[-1]["end_sec"]
    (tmp_path / "manifest.json").write_text(json.dumps({"title": plan.title, "lang": "en", "total_sec": total,
                                                        "audio": "lesson_audio.wav", "scenes": timing}), encoding="utf-8")
    stages = []
    t0 = time.perf_counter()
    render_and_mux_mp4(tmp_path, "en", lambda s, p: stages.append(s))
    elapsed = time.perf_counter() - t0
    info = assert_mp4_ok(tmp_path, total)
    assert "render" in stages and "encode" in stages
    assert not (tmp_path / "lesson.partial.mp4").exists()
    print(f"export {total:.1f}s lesson in {elapsed:.1f}s, {info['kb']:.0f} KB")


@pytest.fixture
def api(monkeypatch):
    require_exporter()
    from fastapi.testclient import TestClient
    from exporter import app as app_module
    app_module.app.state.skip_warmup = True
    monkeypatch.setitem(app_module.state, "languages", ["en"])
    monkeypatch.setattr(app_module.app.state, "generate",
                        lambda topic, lang, cb, **opts: pipeline.generate_lesson(topic, lang, cb, tts=WordRateTTS(),
                                                                                 plan_fn=golden_plan, **opts))
    topic = f"E2E Offline {uuid.uuid4().hex[:6]}"
    with TestClient(app_module.app) as client:
        yield client, topic
    shutil.rmtree(pipeline.artifact_dir(topic, "en"), ignore_errors=True)


def poll(client, job_id, timeout=300):
    end = time.time() + timeout
    while time.time() < end:
        st = client.get(f"/api/status/{job_id}").json()
        if st["stage"] in ("done", "error"):
            return st
        time.sleep(0.4)
    raise AssertionError("job did not finish")


def test_d7_api_generate_poll_download(api):
    client, topic = api
    assert client.get("/api/languages").json() == ["en"]
    health = client.get("/api/health").json()
    assert health["ffmpeg"] is True and health["offline_flags"] is True
    st = poll(client, client.post("/api/generate", json={"topic": topic, "lang": "en"}).json()["job_id"])
    assert st["stage"] == "done" and st["error"] is None, st
    assert {"plan", "tts"} <= set(st["stage_times"]) and st["telemetry"]["stage_sec"]["total"] > 0
    mp4 = client.get(st["mp4_url"])
    assert mp4.status_code == 200 and len(mp4.content) > 150 * 1024
    manifest = client.get(st["manifest_url"]).json()
    assert_mp4_ok(pipeline.artifact_dir(topic, "en"), manifest["total_sec"])


def test_artifact_cache_hit_serves_mp4(api):
    client, topic = api
    first = poll(client, client.post("/api/generate", json={"topic": topic, "lang": "en"}).json()["job_id"])
    assert first["stage"] == "done" and first["cached"] is False
    t0 = time.perf_counter()
    second = client.get(f"/api/status/{client.post('/api/generate', json={'topic': topic, 'lang': 'en'}).json()['job_id']}").json()
    assert second["stage"] == "done" and second["cached"] is True and second["mp4_url"] == first["mp4_url"]
    assert (time.perf_counter() - t0) < 0.5
    assert client.get(second["mp4_url"]).status_code == 200


def test_cache_hit_respects_level_and_length(api):
    # A cached 60 s beginner video is not an answer to a 90 s request: that is how "asked 90, got 60" shipped.
    client, topic = api
    first = poll(client, client.post("/api/generate", json={"topic": topic, "lang": "en"}).json()["job_id"])
    assert first["stage"] == "done"
    try:
        longer = poll(client, client.post("/api/generate",
                                          json={"topic": topic, "lang": "en", "target_sec": 90}).json()["job_id"])
        assert longer["stage"] == "done" and longer["cached"] is False and longer["mp4_url"] != first["mp4_url"]
    finally:
        shutil.rmtree(pipeline.artifact_dir(topic, "en", "beginner", 90), ignore_errors=True)


def test_api_rejects_bad_input(api):
    client, _ = api
    assert client.post("/api/generate", json={"topic": "x", "lang": "en"}).status_code == 422
    assert client.post("/api/generate", json={"topic": "Monsoon", "lang": "xx"}).status_code == 400


@pytest.mark.skipif(os.environ.get("E2E_REAL") != "1", reason="real-model run: set E2E_REAL=1")
@pytest.mark.parametrize("lang", ["en", "hi", "kn"])
def test_d7_real_pipeline_ohms_law(lang):
    require_exporter()
    out = pipeline.generate_lesson("Ohm's Law", lang)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert_mp4_ok(out, manifest["total_sec"])
    if lang == "kn":
        text = " ".join(s["narration"] for s in manifest["scenes"])
        assert any("ಀ" <= c <= "೿" for c in text) and not any("ऀ" <= c <= "ॿ" for c in text)


def test_one_server_serves_ui_renderer_fonts_fixtures(api):
    client, _ = api
    root = client.get("/", follow_redirects=False)
    assert root.status_code in (302, 307) and root.headers["location"] == "/web/index.html"  # live mode, no ?mock=1
    assert client.get("/web/index.html").status_code == 200
    assert client.get("/renderer/player.html").status_code == 200
    font = client.get("/renderer/assets/fonts/NotoSansKannada-Regular.ttf")
    assert font.status_code == 200 and len(font.content) > 100_000
    assert client.get("/assets/fonts/NotoSansDevanagari-Regular.ttf").status_code == 200
    assert client.get("/fixtures/golden_ohms_law.json").json()["title"].startswith("Ohm")
