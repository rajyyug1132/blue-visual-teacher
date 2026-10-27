"""FastAPI backend (AYUSH_BLUEPRINT 4): JSON API + static mounts, one generation at a time.
Persists users, sessions, and lesson history in SQLite with strict security.

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
from typing import Optional, Any, Dict, List

from fastapi import FastAPI, HTTPException, Request, Response, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from orchestrator import pipeline
from orchestrator.cache import topic_slug
from exporter.auth import db as auth_db

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("bvt")
EXAMPLES = ["Ohm's Law", "Photosynthesis", "Binary Search", "Pythagoras Theorem", "Water Cycle", "Supply and Demand",
            "Newton's Third Law", "Monsoon", "DNA Replication", "GST"]
FRIENDLY = {
    "DurationGateError": "The narration came out too short or too long for a 30-90 second video. Please try again.",
    "OfflineViolation": "The renderer tried to use the network, so the export was stopped.",
}

# Initialize SQLite database schema
auth_db.init_db()

app = FastAPI(title="Blue Visual Teacher", docs_url=None, redoc_url=None)

# CORS configuration for local Next.js frontend (e.g. port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs: dict[str, dict] = {}
run_lock = threading.Lock()  # one generation at a time: GPU and models are shared
state = {"models_loaded": False, "languages": ["en"]}


# Request Models
class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=150)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=150)
    password: str = Field(..., min_length=1, max_length=128)


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=120)
    lang: Optional[str] = "en"
    language: Optional[str] = None
    level: Optional[str] = "beginner"
    target_sec: Optional[int] = 60

    @model_validator(mode="before")
    @classmethod
    def resolve_lang(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Accept either 'lang' or 'language' interchangeably
            val = data.get("lang") or data.get("language")
            if val is not None:
                data["lang"] = str(val).strip().lower()
                data["language"] = data["lang"]
        return data


# Authentication Dependency
def get_current_user_optional(request: Request, authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    token = None
    # 1. Bearer header
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    # 2. Cookie fallback
    if not token:
        token = request.cookies.get("bvt_session")
    if token:
        return auth_db.get_user_from_session(token)
    return None


def get_current_user(user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)) -> Dict[str, Any]:
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


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
        job["status"] = "processing"
        job["pct"] = int(pct)
        # Update SQLite if job belongs to a registered user
        if job.get("user_id"):
            auth_db.record_lesson(
                job_id, job["user_id"], job["topic"], job["lang"],
                status="processing", pct=job["pct"], stage=job["stage"]
            )

    with run_lock:
        try:
            out = app.state.generate(job["topic"], job["lang"], progress, level=job.get("level") or "beginner",
                                     target_sec=job.get("target_sec") or 60)
            _urls(job, out)
            tel = out / "telemetry.json"
            if tel.exists():
                import json
                job["telemetry"] = json.loads(tel.read_text(encoding="utf-8"))
                job["profiler"] = job["telemetry"].get("profiler", {})
            job.update(stage="done", status="completed", pct=100)
            if job.get("user_id"):
                auth_db.record_lesson(
                    job_id, job["user_id"], job["topic"], job["lang"],
                    status="completed", pct=100, stage="done",
                    mp4_url=job.get("mp4_url"), manifest_url=job.get("manifest_url"), audio_url=job.get("audio_url")
                )
        except Exception as exc:
            log.error("job %s failed:\n%s", job_id, traceback.format_exc())
            err_msg = FRIENDLY.get(type(exc).__name__, "Something went wrong while making this lesson. Please retry.")
            job.update(stage="error", status="failed", error=err_msg)
            if job.get("user_id"):
                auth_db.record_lesson(
                    job_id, job["user_id"], job["topic"], job["lang"],
                    status="failed", pct=job.get("pct", 0), stage="error",
                    error=err_msg
                )



class ReplanSceneRequest(BaseModel):
    topic: str
    scene_id: int
    current_scene: Optional[Dict[str, Any]] = None
    lang: Optional[str] = "en"

@app.on_event("startup")
def _startup() -> None:
    def load():
        try:
            pipeline.warmup()
            state["languages"] = list(dict.fromkeys((pipeline.available_languages() or []) + ["en", "hi", "kn"]))
            state["models_loaded"] = True
        except Exception:
            log.error("warmup failed:\n%s", traceback.format_exc())
    if not getattr(app.state, "skip_warmup", False):
        threading.Thread(target=load, daemon=True).start()


app.state.generate = pipeline.generate_lesson


# --- AUTHENTICATION ENDPOINTS ---
@app.post("/api/auth/signup")
def signup(req: SignupRequest, response: Response) -> dict:
    try:
        user = auth_db.create_user(req.name, req.email, req.password)
        token = auth_db.create_session(user["id"])
        response.set_cookie(
            key="bvt_session",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=7 * 86400
        )
        return {"user": user, "token": token}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
def login(req: LoginRequest, response: Response) -> dict:
    user = auth_db.authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth_db.create_session(user["id"])
    response.set_cookie(
        key="bvt_session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=7 * 86400
    )
    return {"user": user, "token": token}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, authorization: Optional[str] = Header(None)) -> dict:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        token = request.cookies.get("bvt_session")
    if token:
        auth_db.delete_session(token)
    response.delete_cookie(key="bvt_session")
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: Dict[str, Any] = Depends(get_current_user)) -> dict:
    return {"user": user}


# --- LESSONS & HISTORY ENDPOINTS ---
@app.get("/api/lessons/history")
def lesson_history(user: Dict[str, Any] = Depends(get_current_user)) -> list[dict]:
    return auth_db.get_user_lessons(user["id"])


@app.post("/api/generate")
def generate(req: GenerateRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)) -> dict:
    topic = req.topic.strip()
    target_lang = req.lang or "en"
    if target_lang not in state["languages"]:
        raise HTTPException(400, f"language '{target_lang}' is not available on this machine")
    job_id = uuid.uuid4().hex[:12]
    user_id = current_user["id"] if current_user else None

    job = {
        "job_id": job_id, "user_id": user_id, "topic": topic, "lang": target_lang, "level": req.level or "beginner", "target_sec": req.target_sec or 60,
        "status": "queued", "stage": "queued", "pct": 0, "stage_times": {}, "telemetry": {}, "error": None,
        "mp4_url": None, "manifest_url": None, "audio_url": None, "cached": False
    }
    jobs[job_id] = job

    # Record in SQLite if authenticated
    if user_id:
        auth_db.record_lesson(job_id, user_id, topic, target_lang, status="queued", pct=0, stage="queued")

    hit = pipeline.cached_artifact(topic, target_lang, level=job["level"], target_sec=job["target_sec"])
    if hit:
        _urls(job, hit)
        from orchestrator.planner import StageProfiler
        profiler = StageProfiler(cache_hit=True)
        prof_data = profiler.to_dict()
        tel_file = hit / "telemetry.json"
        if tel_file.exists():
            try:
                import json
                job["telemetry"] = json.loads(tel_file.read_text(encoding="utf-8"))
                if "profiler" in job["telemetry"]:
                    prof_data.update(job["telemetry"]["profiler"])
                    prof_data["cache_hit"] = True
            except Exception:
                pass
        job["profiler"] = prof_data
        job.update(stage="done", status="completed", pct=100, cached=True)
        if user_id:
            auth_db.record_lesson(
                job_id, user_id, topic, target_lang,
                status="completed", pct=100, stage="done",
                mp4_url=job["mp4_url"], manifest_url=job["manifest_url"], audio_url=job["audio_url"]
            )
    else:
        threading.Thread(target=_run, args=(job_id,), daemon=True).start()
    return {
        "job_id": job_id,
        "id": job_id,
        "status": job["status"],
        "stage": job["stage"],
        "pct": job["pct"],
        "mp4_url": job.get("mp4_url"),
        "video_url": job.get("mp4_url"),
        "manifest_url": job.get("manifest_url"),
        "telemetry": job.get("telemetry"),
        "profiler": job.get("profiler"),
    }


@app.get("/api/status/{job_id}")
def status(job_id: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)) -> dict:
    # 1. Check in-memory active jobs
    if job_id in jobs:
        j = jobs[job_id]
        # Check ownership if owned
        if j.get("user_id") and current_user and j["user_id"] != current_user["id"]:
            raise HTTPException(403, "Access denied to this lesson")
        return j

    # 2. Check SQLite persistent store
    stored = auth_db.get_lesson_by_id(job_id)
    if stored:
        if current_user and stored["user_id"] != current_user["id"]:
            raise HTTPException(403, "Access denied to this lesson")
        return {
            "job_id": stored["id"],
            "topic": stored["topic"],
            "lang": stored["lang"],
            "stage": stored["stage"],
            "pct": stored["pct"],
            "status": stored["status"],
            "mp4_url": stored["mp4_url"],
            "manifest_url": stored["manifest_url"],
            "audio_url": stored["audio_url"],
            "error": stored["error"]
        }

    raise HTTPException(404, "unknown job")

@app.post("/api/replan_scene")
@app.post("/replan_scene")
def replan_scene_endpoint(req: ReplanSceneRequest) -> dict:
    from orchestrator.planner import replan_single_scene
    topic = req.topic.strip()
    scene_id = req.scene_id
    lang = req.lang or "en"
    result = replan_single_scene(topic, scene_id, req.current_scene, lang)
    return result



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


# Mount static assets
MOUNTS = (("/renderer/assets/fonts", ROOT / "assets" / "fonts"), ("/assets/fonts", ROOT / "assets" / "fonts"),
          ("/web", ROOT / "web"), ("/renderer", ROOT / "renderer"), ("/fixtures", ROOT / "fixtures"),
          ("/artifacts", pipeline.ARTIFACTS))
for mount, folder in MOUNTS:
    folder.mkdir(parents=True, exist_ok=True)
    app.mount(mount, StaticFiles(directory=folder, html=True), name=mount.strip("/").replace("/", "_"))

__all__ = ["app", "topic_slug"]
