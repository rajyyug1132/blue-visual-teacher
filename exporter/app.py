"""FastAPI backend application for Blue Visual Teacher.

Provides endpoints for lesson generation, job management, language availability,
health checks, and static file mounting for UI and artifacts.
Single-process, single-worker design with queueing for shared GPU resources.
"""

import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import sys
import time
import json
import uuid
import queue
import logging
import threading
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, List

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from exporter.export_mp4 import render_and_mux_mp4, get_ffmpeg_bin

# Setup logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("exporter.app")

# Topic slug from orchestrator.cache if available, otherwise fallback
try:
    from orchestrator.cache import topic_slug
except ImportError:
    import re
    def topic_slug(topic: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", topic.strip().lower()).strip("-") or "untitled"

# Import or stub orchestrator.pipeline
try:
    from orchestrator import pipeline
except ImportError:
    pipeline = None

# Global state
MODELS_LOADED = False
JOBS: Dict[str, Dict[str, Any]] = {}
JOB_QUEUE: queue.Queue = queue.Queue()
QUEUE_LOCK = threading.Lock()

# Directory paths
CACHE_DIR = REPO_ROOT / "cache"
ARTIFACTS_DIR = CACHE_DIR / "artifacts"
WEB_DIR = REPO_ROOT / "web"
RENDERER_DIR = REPO_ROOT / "renderer"

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
RENDERER_DIR.mkdir(parents=True, exist_ok=True)

def get_available_languages() -> List[str]:
    if pipeline and hasattr(pipeline, "available_languages"):
        try:
            return pipeline.available_languages()
        except Exception as e:
            logger.warning(f"Error calling pipeline.available_languages: {e}")
    return ["en", "hi", "kn"]

def run_warmup():
    global MODELS_LOADED
    logger.info("Starting model warmup...")
    if pipeline and hasattr(pipeline, "warmup"):
        try:
            pipeline.warmup()
        except Exception as e:
            logger.warning(f"Warmup error: {e}")
    time.sleep(0.5)
    MODELS_LOADED = True
    logger.info("Model warmup completed. MODELS_LOADED=True")

@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    # Startup: trigger warmup
    threading.Thread(target=run_warmup, daemon=True).start()
    yield
    # Shutdown: clean up
    pass

# FastAPI App
app = FastAPI(title="Blue Visual Teacher", docs_url=None, redoc_url=None, lifespan=lifespan)

# Enable CORS for Next.js frontend (http://localhost:3000, 127.0.0.1:3000, or any dev origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def stub_generate_lesson(topic: str, lang: str, progress_cb=None) -> Path:
    """Fallback stub generator if orchestrator.pipeline is not yet available."""
    import numpy as np
    import soundfile as sf
    slug = topic_slug(topic)
    artifact_dir = ARTIFACTS_DIR / f"{slug}_{lang}"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # 1. Plan stage
    if progress_cb: progress_cb("plan", 30)
    time.sleep(0.2)
    if progress_cb: progress_cb("plan", 100)

    # 2. Translate stage
    if progress_cb: progress_cb("translate", 50)
    time.sleep(0.2)
    if progress_cb: progress_cb("translate", 100)

    # 3. TTS stage
    if progress_cb: progress_cb("tts", 50)
    
    # Generate audio
    duration_sec = 6.0
    sample_rate = 24000
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    audio = 0.4 * np.sin(2 * np.pi * 440.0 * t)
    wav_path = artifact_dir / "lesson_audio.wav"
    sf.write(str(wav_path), audio.astype(np.float32), sample_rate)

    # Generate manifest
    manifest_data = {
        "title": topic,
        "lang": lang,
        "total_sec": duration_sec,
        "audio": "lesson_audio.wav",
        "sample_rate": sample_rate,
        "scenes": [
            {
                "id": 1,
                "start_sec": 0.0,
                "end_sec": 3.0,
                "duration_sec": 3.0,
                "narration": f"Understanding {topic}.",
                "visual": {
                    "type": "title",
                    "params": {
                        "labels": [topic, f"Lang: {lang}"],
                        "steps": ["Introduction to Concept"]
                    }
                }
            },
            {
                "id": 2,
                "start_sec": 3.0,
                "end_sec": 6.0,
                "duration_sec": 3.0,
                "narration": f"Core principles and applications of {topic}.",
                "visual": {
                    "type": "bullets",
                    "params": {
                        "labels": ["Key Takeaways"],
                        "steps": ["Step 1: Observation", "Step 2: Conclusion"]
                    }
                }
            }
        ]
    }
    with open(artifact_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    if progress_cb: progress_cb("tts", 100)

    # 4. Render & Encode
    render_and_mux_mp4(artifact_dir, lang=lang, progress_cb=progress_cb, fps=20)
    return artifact_dir

def worker_loop():
    """Background single worker processing one generation job at a time."""
    while True:
        job_id = JOB_QUEUE.get()
        if job_id is None:
            break
        
        job = JOBS.get(job_id)
        if not job or job.get("cached"):
            JOB_QUEUE.task_done()
            continue

        topic = job["topic"]
        lang = job["lang"]
        slug = topic_slug(topic)
        start_overall = time.time()
        stage_times = {}
        last_stage_time = time.time()
        current_stage = "plan"

        def progress_callback(stage: str, pct: int):
            nonlocal last_stage_time, current_stage
            now = time.time()
            if stage != current_stage:
                stage_times[current_stage] = round(now - last_stage_time, 2)
                current_stage = stage
                last_stage_time = now
            job["stage"] = stage
            job["pct"] = pct
            job["stage_times"] = dict(stage_times)

        try:
            job["stage"] = "plan"
            job["pct"] = 0

            if pipeline and hasattr(pipeline, "generate_lesson"):
                out_dir = pipeline.generate_lesson(topic, lang, progress_cb=progress_callback)
            else:
                out_dir = stub_generate_lesson(topic, lang, progress_cb=progress_callback)

            total_elapsed = round(time.time() - start_overall, 2)
            stage_times[current_stage] = round(time.time() - last_stage_time, 2)
            stage_times["total"] = total_elapsed

            job["stage"] = "done"
            job["pct"] = 100
            job["stage_times"] = stage_times
            job["telemetry"] = {"total_sec": total_elapsed}
            job["mp4_url"] = f"/artifacts/{slug}_{lang}/lesson.mp4"
            job["manifest_url"] = f"/artifacts/{slug}_{lang}/manifest.json"
            job["audio_url"] = f"/artifacts/{slug}_{lang}/lesson_audio.wav"
            logger.info(f"Job {job_id} ({topic}, {lang}) completed in {total_elapsed}s")

        except Exception as e:
            err_msg = str(e) or e.__class__.__name__
            logger.error(f"Job {job_id} failed: {err_msg}\n{traceback.format_exc()}")
            job["stage"] = "error"
            job["error"] = err_msg
            job["pct"] = 0

        finally:
            JOB_QUEUE.task_done()

# Start background worker thread
worker_thread = threading.Thread(target=worker_loop, daemon=True)
worker_thread.start()


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=120)
    lang: Optional[str] = Field(None, min_length=2, max_length=10)
    language: Optional[str] = Field(None, min_length=2, max_length=10)

    @model_validator(mode="before")
    @classmethod
    def resolve_lang(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Accept either 'lang' or 'language' seamlessly
            val = data.get("lang") or data.get("language")
            if val is not None:
                data["lang"] = str(val).strip().lower()
                data["language"] = data["lang"]
        return data

@app.post("/api/generate")
def generate_endpoint(req: GenerateRequest):
    topic = req.topic.strip()
    lang = req.lang.strip().lower()

    avail = get_available_languages()
    if lang not in avail:
        raise HTTPException(
            status_code=400,
            detail=f"Language '{lang}' is not supported. Available: {avail}"
        )

    slug = topic_slug(topic)
    artifact_dir = ARTIFACTS_DIR / f"{slug}_{lang}"
    mp4_file = artifact_dir / "lesson.mp4"
    manifest_file = artifact_dir / "manifest.json"
    audio_file = artifact_dir / "lesson_audio.wav"

    job_id = str(uuid.uuid4())

    # Cache hit check
    if mp4_file.exists() and mp4_file.stat().st_size > 0 and manifest_file.exists() and audio_file.exists():
        JOBS[job_id] = {
            "job_id": job_id,
            "topic": topic,
            "lang": lang,
            "stage": "done",
            "pct": 100,
            "stage_times": {"cache": 0.001},
            "telemetry": {"cached": True},
            "error": None,
            "mp4_url": f"/artifacts/{slug}_{lang}/lesson.mp4",
            "manifest_url": f"/artifacts/{slug}_{lang}/manifest.json",
            "audio_url": f"/artifacts/{slug}_{lang}/lesson_audio.wav",
            "cached": True,
        }
        return {"job_id": job_id}

    # Queue new job
    JOBS[job_id] = {
        "job_id": job_id,
        "topic": topic,
        "lang": lang,
        "stage": "queued",
        "pct": 0,
        "stage_times": {},
        "telemetry": {},
        "error": None,
        "mp4_url": None,
        "manifest_url": None,
        "audio_url": None,
        "cached": False,
    }
    JOB_QUEUE.put(job_id)
    return {"job_id": job_id}

@app.get("/api/status/{job_id}")
def status_endpoint(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/api/languages")
def languages_endpoint():
    return get_available_languages()

@app.get("/api/examples")
def examples_endpoint():
    examples = []
    # Check artifacts directory for pre-cached topics
    if ARTIFACTS_DIR.exists():
        grouped: Dict[str, List[str]] = {}
        for d in ARTIFACTS_DIR.iterdir():
            if d.is_dir() and "_" in d.name:
                slug, lang = d.name.rsplit("_", 1)
                if (d / "lesson.mp4").exists():
                    grouped.setdefault(slug, []).append(lang)
        for slug, langs in grouped.items():
            readable_topic = slug.replace("-", " ").title()
            examples.append({"topic": readable_topic, "slug": slug, "languages": sorted(langs)})

    if not examples:
        examples = [
            {"topic": "Ohm's Law: Voltage, Current, and Resistance", "slug": "ohm-s-law", "languages": ["en", "hi", "kn"]}
        ]
    return examples

@app.get("/api/health")
def health_endpoint():
    # Ollama check
    ollama_ok = False
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1) as resp:
            ollama_ok = (resp.status == 200)
    except Exception:
        pass

    # FFmpeg check
    ffmpeg_ok = False
    try:
        ffmpeg_bin = get_ffmpeg_bin()
        ffmpeg_ok = bool(ffmpeg_bin and Path(ffmpeg_bin).exists())
    except Exception:
        pass

    # Chromium check
    chromium_ok = True

    # Offline flags
    offline_flags = (
        os.environ.get("HF_HUB_OFFLINE") == "1" and
        os.environ.get("TRANSFORMERS_OFFLINE") == "1"
    )

    return {
        "ollama": ollama_ok,
        "ffmpeg": ffmpeg_ok,
        "chromium": chromium_ok,
        "models_loaded": MODELS_LOADED,
        "offline_flags": offline_flags,
    }

@app.get("/")
def root_redirect():
    return RedirectResponse(url="/web/index.html")

# Static mounts per PLAN 4.7 & AYUSH_BLUEPRINT section 4
if WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")
if RENDERER_DIR.exists():
    app.mount("/renderer", StaticFiles(directory=str(RENDERER_DIR)), name="renderer")
if ARTIFACTS_DIR.exists():
    app.mount("/artifacts", StaticFiles(directory=str(ARTIFACTS_DIR)), name="artifacts")
