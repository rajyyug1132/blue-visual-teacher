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
import re
import threading
import time
from pathlib import Path

from orchestrator.cache import topic_slug

DURATION_MIN_SEC, DURATION_MAX_SEC = 30.0, 90.0
ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "cache" / "artifacts"
STAGES = ("plan", "translate", "tts", "render", "encode", "done")
LEVELS = ("beginner", "intermediate")
DEFAULT_LEVEL, DEFAULT_TARGET_SEC = "beginner", 60

_engines: dict = {}
_engines_lock = threading.Lock()


def request_options(level: str | None = None, target_sec: int | None = None) -> tuple[str, int]:
    """Clamp the two Stage 1 inputs (CC-2) so a bad request can never reach the planner or the cache key."""
    level = level if level in LEVELS else DEFAULT_LEVEL
    try:
        target = int(target_sec) if target_sec is not None else DEFAULT_TARGET_SEC
    except (TypeError, ValueError):
        target = DEFAULT_TARGET_SEC
    return level, max(int(DURATION_MIN_SEC), min(int(DURATION_MAX_SEC), target))


def artifact_dir(topic: str, lang: str, level: str = DEFAULT_LEVEL,
                 target_sec: int = DEFAULT_TARGET_SEC) -> Path:
    """One directory per (topic, language, level, length); the default pair keeps the historical name."""
    level, target_sec = request_options(level, target_sec)
    suffix = "" if (level, target_sec) == (DEFAULT_LEVEL, DEFAULT_TARGET_SEC) else f"__{level}__{target_sec}s"
    return ARTIFACTS / f"{topic_slug(topic)}_{lang}{suffix}"


def cached_artifact(topic: str, lang: str, level: str = DEFAULT_LEVEL,
                    target_sec: int = DEFAULT_TARGET_SEC) -> Path | None:
    """Tier 2: a complete lesson (manifest + MP4) for this (topic, lang, level, length), or None."""
    out = artifact_dir(topic, lang, level, target_sec)
    return out if (out / "manifest.json").exists() and (out / "lesson.mp4").exists() else None


def warmup(planner: bool = True) -> dict:
    """Load translator and TTS once (and pin the Ollama planner); later calls reuse them."""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    with _engines_lock:
        if "tts" not in _engines:
            from localization.tts_engine import OfflineTTSEngine
            _engines["tts"] = OfflineTTSEngine(voice_en="af_heart")
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


def generate_lesson(topic: str, lang: str, progress_cb=None, *, level: str = DEFAULT_LEVEL,
                    target_sec: int = DEFAULT_TARGET_SEC, tts=None, translator=None, export=None,
                    plan_fn=None) -> Path:
    """Topic -> narrated MP4 in cache/artifacts/{slug}_{lang}/. tts/translator/export/plan_fn are injectable for tests."""
    report = progress_cb or (lambda stage, pct: None)
    level, target_sec = request_options(level, target_sec)
    hit = cached_artifact(topic, lang, level, target_sec)
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
        from orchestrator.planner import plan_lesson
        plan, telemetry = stage("plan", lambda: plan_lesson(topic, level=level, target_sec=target_sec))
    else:
        plan, telemetry = stage("plan", lambda: plan_fn(topic))

    if lang != "en":
        translator = translator or warmup(planner=False)["translator"]
        localized = stage("translate", lambda: translator.localize_lesson(plan, lang))
    else:
        localized = plan
        times["translate"] = 0.0

    out = artifact_dir(topic, lang, level, target_sec)
    out.mkdir(parents=True, exist_ok=True)
    wav = out / "lesson_audio.wav"
    tts = tts or warmup(planner=False)["tts"]
    timing = stage("tts", lambda: tts.synthesize_all_scenes(localized.scenes, lang, str(wav)))
    if timing and timing[-1]["end_sec"] > DURATION_MAX_SEC:
        localized = localized.model_copy(deep=True)  # never edit the cached English plan
        start = time.perf_counter()
        timing, trims = fit_duration(localized, timing, tts, lang, wav)
        times["duration_fit"] = round(time.perf_counter() - start, 3)
        telemetry = {**telemetry, "duration_trims": trims}
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
    (out / "telemetry.json").write_text(json.dumps({"topic": topic, "lang": lang, "level": level,
                                                    "target_sec": target_sec, "stage_sec": times,
                                                    "planner": telemetry}, ensure_ascii=False, indent=2,
                                                   default=str), encoding="utf-8")
    report("done", 100)
    return out


SENTENCE_END = re.compile(r"(?<=[.!?।|])\s+")  # includes the Devanagari danda
MAX_FIT_PASSES = 4
MIN_SCENES = 4


def _sentences(text: str) -> list[str]:
    return [s for s in SENTENCE_END.split(text.strip()) if s]


def fit_duration(localized, timing: list[dict], tts, lang: str, wav: Path) -> tuple[list[dict], list[str]]:
    """Lesson audio over 90 s (Kannada runs ~1.8x the English): shorten instead of rejecting (YYUG_BLUEPRINT 5).

    Each pass makes one cut, then re-synthesizes and re-measures, in this order: drop the last sentence of the
    longest ordinary scene with more than one sentence; else cut the recap scene (keeping MIN_SCENES); else, as a
    last resort, trim the worked example (the scene with a check, whose last sentence speaks the answer).
    Captions use the same trimmed narration, so audio and captions stay in step.
    """
    trims = []
    for _ in range(MAX_FIT_PASSES + 1):
        if timing[-1]["end_sec"] <= DURATION_MAX_SEC:
            break
        order = sorted(range(len(timing)), key=lambda i: -timing[i]["duration_sec"])
        protected = {i for i, s in enumerate(localized.scenes) if getattr(s, "check", None)}
        multi = [i for i in order if len(_sentences(localized.scenes[i].narration)) > 1]
        plain = [i for i in multi if i not in protected]
        if len(trims) >= MAX_FIT_PASSES:
            plain = multi = []
        # Order: trim ordinary scenes -> cut the recap -> trim the worked example (its answer) only as a last resort.
        if plain:
            pick = plain[0]
        elif len(localized.scenes) > MIN_SCENES:
            dropped = localized.scenes.pop()  # the recap
            trims.append(f"scene {dropped.id}: cut (recap)")
            timing = tts.synthesize_all_scenes(localized.scenes, lang, str(wav))
            continue
        elif multi:
            pick = multi[0]
        else:
            break
        scene = localized.scenes[pick]
        scene.narration = " ".join(_sentences(scene.narration)[:-1])
        trims.append(f"scene {scene.id}: dropped last sentence")
        timing = tts.synthesize_all_scenes(localized.scenes, lang, str(wav))
    return timing, trims


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
