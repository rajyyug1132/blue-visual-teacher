# orchestrator/pipeline.py — PLAN 4.6 entry point plus the checks that need real TTS output.
#
#   generate_lesson(topic, lang, progress_cb=None) -> Path      cache/artifacts/{slug}_{lang}/
#   warmup()                                                    load every model once, at startup
#   available_languages()                                       languages with real engines on this machine
#
# Stages reported to progress_cb(stage, pct): plan, translate, tts, render, encode, done.
# Tier 1 cache: the English plan by topic (orchestrator/cache.py). Tier 2: the finished artifacts by (topic, lang);
# a hit returns the directory immediately, before any model is touched.
import json
import os
import threading
import time
from pathlib import Path

from orchestrator.cache import topic_slug

DURATION_MIN_SEC, DURATION_MAX_SEC = 30.0, 90.0
ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "cache" / "artifacts"
STAGES = ("plan", "translate", "tts", "render", "encode", "done")

_engines: dict = {}
_engines_lock = threading.Lock()


def artifact_dir(topic: str, lang: str) -> Path:
    return ARTIFACTS / f"{topic_slug(topic)}_{lang}"


def cached_artifact(topic: str, lang: str) -> Path | None:
    """Tier 2: a complete lesson (manifest + MP4) for this (topic, lang), or None."""
    out = artifact_dir(topic, lang)
    return out if (out / "manifest.json").exists() and (out / "lesson.mp4").exists() else None


def warmup(planner: bool = True) -> dict:
    """Load translator and TTS once (and pin the Ollama planner); later calls reuse them."""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    with _engines_lock:
        if "tts" not in _engines:
            from localization.tts_engine import OfflineTTSEngine
            _engines["tts"] = OfflineTTSEngine()
        if "translator" not in _engines:
            from localization.translator import OfflineIndicTranslator
            _engines["translator"] = OfflineIndicTranslator()
    if planner:
        from orchestrator.planner import warm_up_ollama
        try:
            warm_up_ollama()
        except Exception:  # the planner falls back to its ladder/template if Ollama is down; don't block startup
            pass
    return _engines


def available_languages() -> list[str]:
    """Languages whose translation and speech run on real models here (never synthetic audio)."""
    eng = warmup(planner=False)
    tts, tr = eng["tts"], eng["translator"]
    langs = ["en"] if getattr(tts, "kokoro_en", None) is not None else []
    if getattr(tr, "model", None) is not None:
        if getattr(tts, "kokoro_hi", None) is not None or "hi" in getattr(tts, "mms_models", {}):
            langs.append("hi")
        for code in ("kn", "ta", "te"):
            if code in getattr(tts, "mms_models", {}):
                langs.append(code)
    return langs


def generate_lesson(topic: str, lang: str, progress_cb=None, *, tts=None, translator=None, export=None,
                    plan_fn=None) -> Path:
    """Topic -> narrated MP4 in cache/artifacts/{slug}_{lang}/. tts/translator/export/plan_fn are injectable for tests."""
    report = progress_cb or (lambda stage, pct: None)
    hit = cached_artifact(topic, lang)
    if hit:
        report("done", 100)
        return hit

    times, t0 = {}, time.perf_counter()

    def stage(name, fn):
        report(name, 0)
        start = time.perf_counter()
        result = fn()
        times[name] = round(time.perf_counter() - start, 3)
        return result

    if plan_fn is None:
        from orchestrator.planner import plan_lesson as plan_fn
    plan, telemetry = stage("plan", lambda: plan_fn(topic))

    if lang != "en":
        translator = translator or warmup(planner=False)["translator"]
        localized = stage("translate", lambda: translator.localize_lesson(plan, lang))
    else:
        localized = plan
        times["translate"] = 0.0

    out = artifact_dir(topic, lang)
    out.mkdir(parents=True, exist_ok=True)
    wav = out / "lesson_audio.wav"
    tts = tts or warmup(planner=False)["tts"]
    timing = stage("tts", lambda: tts.synthesize_all_scenes(localized.scenes, lang, str(wav)))
    total = duration_gate(timing)

    manifest = {"title": localized.title, "lang": lang, "total_sec": total, "audio": wav.name,
                "sample_rate": 24000, "scenes": timing}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if export is None:
        from exporter.export_mp4 import render_and_mux_mp4 as export
    start = time.perf_counter()
    export(out, lang, report)
    times["render_encode"] = round(time.perf_counter() - start, 3)

    times["total"] = round(time.perf_counter() - t0, 3)
    (out / "telemetry.json").write_text(json.dumps({"topic": topic, "lang": lang, "stage_sec": times,
                                                    "planner": telemetry}, ensure_ascii=False, indent=2,
                                                   default=str), encoding="utf-8")
    report("done", 100)
    return out


class DurationGateError(RuntimeError):
    """Measured lesson audio is outside the 30-90 s window; do not render it."""


def duration_gate(timing_manifest: list[dict]) -> float:
    """Post-TTS gate: return the measured total seconds, or raise before any frames are rendered.

    The schema only estimates duration from word counts; this checks the real audio length, which differs
    by language (Hindi and Kannada narrations run longer than the English plan).
    """
    if not timing_manifest:
        raise DurationGateError("TTS returned no scenes")
    total = timing_manifest[-1]["end_sec"]
    if not DURATION_MIN_SEC <= total <= DURATION_MAX_SEC:
        raise DurationGateError(
            f"lesson audio is {total:.2f}s, outside {DURATION_MIN_SEC:.0f}-{DURATION_MAX_SEC:.0f}s "
            f"({len(timing_manifest)} scenes)"
        )
    return total
