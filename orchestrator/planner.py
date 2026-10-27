# orchestrator/planner.py
import json
import os
import re
import time

import httpx
import ollama
from pydantic import ValidationError

from orchestrator.cache import load_plan, save_plan
from orchestrator.fallbacks import build_safe_fallback_lesson
from orchestrator.prompts import FEW_SHOT_MESSAGES, SYSTEM_PROMPT
from orchestrator.schema import LessonPlan

MODEL_NAME = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")  # Or "llama3.2:3b" / "gemma4:e4b" / "qwen3:4b"
THINKING_MODEL_PREFIXES = ("qwen3", "gemma")  # only these get think=False
TARGET_WORDS = (100, 140)
SAFE_WORDS = (70, 180)  # still lands inside 30-90 s of audio at ~2.3 words/s
KEEP_ALIVE = -1  # must be a number: the string "-1" is rejected by the server ("missing unit in duration")

# Pinned to localhost so a stray OLLAMA_HOST can never route planning off the machine.
_client = ollama.Client(host="http://127.0.0.1:11434", timeout=120)

LLM_ERRORS = (ollama.ResponseError, ConnectionError, httpx.HTTPError)
REPAIR_MAX_WORDS = 30
CLAUSE_BREAK = re.compile(r",\s+(?:where|which|while|so|and|but)\b|;\s+")


def total_words(plan: LessonPlan) -> int:
    return sum(len(s.narration.split()) for s in plan.scenes)


def _chat(**kwargs):
    """Send think=False only to thinking-capable families; retry without it if the model rejects the flag."""
    if not kwargs["model"].lower().startswith(THINKING_MODEL_PREFIXES):
        return _client.chat(**kwargs)
    try:
        return _client.chat(think=False, **kwargs)
    except ollama.ResponseError as exc:
        if "think" not in str(exc).lower():
            raise
        return _client.chat(**kwargs)


def _shorten_narration(text: str) -> str | None:
    """Trim an overlong narration to complete sentences, or to its main clause; None if that is impossible."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = []
    for sentence in sentences:
        if len(" ".join(kept + [sentence]).split()) > REPAIR_MAX_WORDS:
            break
        kept.append(sentence)
    if kept:
        return " ".join(kept)
    # One long sentence (often cut off by the grammar's maxLength): keep the longest main clause that fits.
    heads = [sentences[0][:m.start()] for m in CLAUSE_BREAK.finditer(sentences[0])]
    heads = [h for h in heads if 8 <= len(h.split()) <= REPAIR_MAX_WORDS]
    return heads[-1].rstrip(" ,;:") + "." if heads else None


def _parse_plan(content: str) -> tuple[LessonPlan, bool]:
    """Validate the model output; if only narrations are too long, repair them. Returns (plan, repaired)."""
    try:
        return LessonPlan.model_validate_json(content), False
    except ValidationError as exc:
        try:
            data = json.loads(content)
            for scene in data["scenes"]:
                if len(scene["narration"].split()) > 42:
                    scene["narration"] = _shorten_narration(scene["narration"]) or scene["narration"]
            return LessonPlan.model_validate(data), True
        except (ValueError, KeyError, TypeError, ValidationError):
            raise exc from None


def _validation_feedback(exc: ValidationError) -> str:
    """Turn a ValidationError into per-scene instructions; a raw error dump makes 3B models repeat themselves."""
    lines = []
    for err in exc.errors():
        loc = err["loc"]
        if len(loc) >= 3 and loc[0] == "scenes" and loc[2] == "narration":
            lines.append(
                f"Scene {loc[1] + 1} narration is invalid ({err['msg']}). Rewrite it as 1-2 complete sentences "
                "of 18-28 words. Put formulas and variable definitions in visual.params.labels, not in narration."
            )
        else:
            lines.append(f"{'.'.join(map(str, loc)) or 'JSON'}: {err['msg']}")
    return "Validation failed:\n- " + "\n- ".join(lines)


def warm_up_ollama(model: str = MODEL_NAME) -> None:
    """Pin model in memory at startup so live demo requests incur near-zero load_duration."""
    _client.generate(model=model, prompt="ping", keep_alive=KEEP_ALIVE, options={"num_predict": 1})


def plan_lesson(concept: str, model: str = MODEL_NAME, use_cache: bool = True) -> tuple[LessonPlan, dict]:
    t0 = time.perf_counter()
    if use_cache and (cached := load_plan(concept)) is not None:
        return cached, {"cache_hit": True, "fallback_used": False, "total_words": total_words(cached),
                        "total_sec": round(time.perf_counter() - t0, 4)}

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + FEW_SHOT_MESSAGES + [
        {"role": "user", "content": f"Concept: {concept.strip()}"}
    ]
    best = None  # schema-valid plan whose word total missed the target but is still safe
    errors = []
    for attempt in range(2):
        resp = None
        try:
            resp = _chat(
                model=model,
                messages=messages,
                format=LessonPlan.model_json_schema(),
                keep_alive=KEEP_ALIVE,
                options={"temperature": 0.0 if attempt == 0 else 0.2, "num_ctx": 4096, "num_predict": 850},
            )
            plan, repaired = _parse_plan(resp.message.content or "")
            words = total_words(plan)
            telemetry = {
                "attempt": attempt + 1,
                "cache_hit": False,
                "prompt_tokens": resp.prompt_eval_count or 0,
                "output_tokens": resp.eval_count or 0,
                "load_sec": round((resp.load_duration or 0) / 1e9, 3),
                "eval_sec": round((resp.eval_duration or 0) / 1e9, 3),
                "total_words": words,
                "repaired": repaired,
                "fallback_used": False,
            }
            if TARGET_WORDS[0] <= words <= TARGET_WORDS[1]:
                return _finish(concept, plan, telemetry, t0, use_cache)
            if SAFE_WORDS[0] <= words <= SAFE_WORDS[1]:
                best = (plan, telemetry)
            problem = f"Total narration is {words} words; it must be {TARGET_WORDS[0]}-{TARGET_WORDS[1]} words."
        except LLM_ERRORS as exc:
            # Daemon down or HTTP error: there is no model output to correct, so just retry.
            errors.append(f"{type(exc).__name__}: {exc}")
            continue
        except ValidationError as exc:
            problem = _validation_feedback(exc)
        errors.append(problem)
        messages.append({"role": "assistant", "content": resp.message.content or "{}"})
        messages.append({
            "role": "user",
            "content": f"{problem}\nReturn the full corrected JSON with 4-6 scenes and 18-30 words per narration.",
        })

    if best is not None:
        return _finish(concept, best[0], best[1], t0, use_cache)

    # Deterministic safe template fallback if both LLM attempts fail. Never cached, so a later run can retry the LLM.
    plan = build_safe_fallback_lesson(concept)
    return plan, {"attempt": 3, "cache_hit": False, "fallback_used": True, "total_words": total_words(plan),
                  "errors": errors, "total_sec": round(time.perf_counter() - t0, 3)}


def _finish(concept, plan, telemetry, t0, use_cache):
    telemetry["total_sec"] = round(time.perf_counter() - t0, 3)
    if use_cache:
        save_plan(concept, plan)
    return plan, telemetry
