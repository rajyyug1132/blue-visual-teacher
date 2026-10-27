"""FastAPI backend (AYUSH_BLUEPRINT 4): JSON API + static mounts, one generation at a time.

    python -m uvicorn exporter.app:app --host 127.0.0.1 --port 8000
"""
import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import logging
import shutil
import threading
import time
import traceback
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from orchestrator import pipeline
from orchestrator.cache import topic_slug

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("bvt")
EXAMPLES = ["Ohm's Law", "Photosynthesis", "Binary Search", "Pythagoras Theorem", "Water Cycle", "Supply and Demand",
            "Newton's Third Law", "Monsoon", "DNA Replication", "GST"]
FRIENDLY = {
    "DurationGateError": "The narration came out too short or too long for a 30-90 second video. Please try again.",
    "OfflineViolation": "The renderer tried to use the network, so the export was stopped.",
}

app = FastAPI(title="Blue Visual Teacher", docs_url=None, redoc_url=None)
jobs: dict[str, dict] = {}
run_lock = threading.Lock()  # one generation at a time: GPU and models are shared
state = {"models_loaded": False, "languages": ["en"]}


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=120)
    lang: str = "en"


def _urls(job: dict, out: Path) -> None:
    base = f"/artifacts/{out.name}"
    job.update(mp4_url=f"{base}/lesson.mp4", manifest_url=f"{base}/manifest.json", audio_url=f"{base}/lesson_audio.wav")


def _run(job_id: str) -> None:
    job = jobs[job_id]
    stage_started = {"t": time.perf_counter()}

    def progress(stage: str, pct: int) -> None:
        if stage != job["stage"]:
            if job["stage"] not in ("queued",):
                job["stage_times"][job["stage"]] = round(time.perf_counter() - stage_started["t"], 2)
            stage_started["t"] = time.perf_counter()
            job["stage"] = stage
        job["pct"] = int(pct)

    with run_lock:
        try:
            out = app.state.generate(job["topic"], job["lang"], progress)
            _urls(job, out)
            tel = out / "telemetry.json"
            if tel.exists():
                import json
                job["telemetry"] = json.loads(tel.read_text(encoding="utf-8"))
            job.update(stage="done", pct=100)
        except Exception as exc:
            log.error("job %s failed:\n%s", job_id, traceback.format_exc())
            job.update(stage="error", error=FRIENDLY.get(type(exc).__name__,
                                                         "Something went wrong while making this lesson. Please retry."))


@app.on_event("startup")
def _startup() -> None:
    def load():
        try:
            pipeline.warmup()
            state["languages"] = pipeline.available_languages() or ["en"]
            state["models_loaded"] = True
        except Exception:
            log.error("warmup failed:\n%s", traceback.format_exc())
    if not getattr(app.state, "skip_warmup", False):
        threading.Thread(target=load, daemon=True).start()


app.state.generate = pipeline.generate_lesson


@app.post("/api/generate")
def generate(req: GenerateRequest) -> dict:
    topic = req.topic.strip()
    if req.lang not in state["languages"]:
        raise HTTPException(400, f"language '{req.lang}' is not available on this machine")
    job_id = uuid.uuid4().hex[:12]
    job = {"job_id": job_id, "topic": topic, "lang": req.lang, "stage": "queued", "pct": 0, "stage_times": {},
           "telemetry": {}, "error": None, "mp4_url": None, "manifest_url": None, "audio_url": None, "cached": False}
    jobs[job_id] = job
    hit = pipeline.cached_artifact(topic, req.lang)
    if hit:
        _urls(job, hit)
        job.update(stage="done", pct=100, cached=True)
    else:
        threading.Thread(target=_run, args=(job_id,), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
def status(job_id: str) -> dict:
    if job_id not in jobs:
        raise HTTPException(404, "unknown job")
    return jobs[job_id]


@app.get("/api/languages")
def languages() -> list[str]:
    return state["languages"]


@app.get("/api/examples")
def examples() -> list[dict]:
    return [{"topic": t, "cached": [lang for lang in ("en", "hi", "kn") if pipeline.cached_artifact(t, lang)]}
            for t in EXAMPLES]


@app.get("/api/health")
def health() -> dict:
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=0.5):
            ollama = True
    except OSError:
        ollama = False
    return {"ollama": ollama, "ffmpeg": bool(shutil.which("ffmpeg")), "models_loaded": state["models_loaded"],
            "offline_flags": os.environ.get("HF_HUB_OFFLINE") == "1" and os.environ.get("TRANSFORMERS_OFFLINE") == "1",
            "languages": state["languages"]}


@app.get("/")
def index() -> RedirectResponse:
    return RedirectResponse("/web/index.html")


for mount, folder in (("/web", ROOT / "web"), ("/renderer", ROOT / "renderer"), ("/artifacts", pipeline.ARTIFACTS)):
    folder.mkdir(parents=True, exist_ok=True)
    app.mount(mount, StaticFiles(directory=folder, html=True), name=mount.strip("/"))

__all__ = ["app", "topic_slug"]
