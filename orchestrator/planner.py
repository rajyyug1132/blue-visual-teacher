# orchestrator/planner.py
import copy
import json
import os
import re
import time

import httpx
import ollama
from pydantic import ValidationError

from orchestrator.cache import load_plan, save_plan
from orchestrator.fallbacks import build_safe_fallback_lesson
from orchestrator.mathcheck import MathCheckError, make_qualitative, verify_plan
from orchestrator.prompts import FEW_SHOT_MESSAGES, SYSTEM_PROMPT
from orchestrator.schema import NOT_SPOKEN, TOTAL_MAX, TOTAL_MIN, WORDS_MAX, WORDS_MIN, LessonPlan
from orchestrator.spoken import to_spoken

MODEL_NAME = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")  # GPU gets the planner; TTS/MT run on CPU (DEVICE)
THINKING_MODEL_PREFIXES = ("qwen3", "gemma")  # only these get think=False
KEEP_ALIVE = -1  # must be a number: the string "-1" is rejected by the server ("missing unit in duration")

# Pinned to localhost so a stray OLLAMA_HOST can never route planning off the machine.
_client = ollama.Client(host="http://127.0.0.1:11434", timeout=120)

LLM_ERRORS = (ollama.ResponseError, ConnectionError, httpx.HTTPError)
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
        if len(" ".join(kept + [sentence]).split()) > WORDS_MAX:
            break
        kept.append(sentence)
    if kept and len(" ".join(kept).split()) >= WORDS_MIN:
        return " ".join(kept)
    # Whole sentences don't fit (one long sentence, often cut off by the grammar's maxLength, or a short sentence
    # followed by a long one): keep the longest prefix that ends at a clause break and fits.
    full = text.strip()
    heads = [full[:m.start()] for m in CLAUSE_BREAK.finditer(full)]
    heads = [h for h in heads if WORDS_MIN <= len(h.split()) <= WORDS_MAX]
    return heads[-1].rstrip(" ,;:") + "." if heads else None


def _parse_plan(content: str, last_attempt: bool) -> tuple[LessonPlan, bool, dict]:
    """parse -> verify math (digits still present) -> to_spoken -> trim -> schema validate.

    Returns (plan, repaired, math). Raises ValidationError, or MathCheckError unless this is the last attempt,
    in which case an unverifiable worked example is swapped for a qualitative one.
    """
    try:
        data = json.loads(content)
        scenes = data["scenes"]
        assert isinstance(scenes, list) and all(isinstance(s, dict) for s in scenes)
    except (ValueError, KeyError, TypeError, AssertionError):
        return LessonPlan.model_validate_json(content), False, {}  # raises a ValidationError describing the shape

    try:
        math = verify_plan(data)
    except MathCheckError as exc:
        if not last_attempt:
            exc.salvage = _salvage(data)  # used if the retry fails for any reason
            raise
        math = make_qualitative(data)
    except (KeyError, TypeError, AttributeError):
        math = {"status": "unchecked"}  # malformed scene; schema validation below reports it

    plan, repaired = _spoken_and_validate(data)
    return plan, repaired, math


def _salvage(data: dict) -> tuple[LessonPlan, bool, dict] | None:
    """This plan with its worked example made qualitative, if that makes it valid."""
    data = copy.deepcopy(data)
    math = make_qualitative(data)
    try:
        plan, repaired = _spoken_and_validate(data)
    except ValidationError:
        return None
    return plan, repaired, math


def _spoken_and_validate(data: dict) -> tuple[LessonPlan, bool]:
    """Spell out digits/symbols, trim overlong narrations, then validate against the schema."""
    repaired = False
    for scene in data["scenes"]:
        narration = scene.get("narration")
        if not isinstance(narration, str):
            continue
        if NOT_SPOKEN.search(narration):
            narration = to_spoken(narration)  # spelling out can add words, so trim after
        if len(narration.split()) > WORDS_MAX:
            narration = _shorten_narration(narration) or narration
        repaired |= narration != scene["narration"]
        scene["narration"] = narration
    return LessonPlan.model_validate(data), repaired


def _validation_feedback(exc: ValidationError) -> str:
    """Turn a ValidationError into per-scene instructions; a raw error dump makes 3B models repeat themselves."""
    lines = []
    for err in exc.errors():
        loc = err["loc"]
        if len(loc) >= 3 and loc[0] == "scenes" and loc[2] == "narration":
            lines.append(
                f"Scene {loc[1] + 1} narration is invalid ({err['msg']}). Rewrite it as 1-2 complete sentences "
                "of 18-28 spoken words, with every number written in words. Put digits, formulas and variable "
                "definitions in visual.params.labels, not in narration."
            )
        elif not loc and "total" in err["msg"]:
            lines.append(f"{err['msg']}. Lengthen or shorten scenes so all narrations add up to "
                         f"{TOTAL_MIN}-{TOTAL_MAX} words.")
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
    errors = []
    salvage = None  # attempt 1 with a qualitative worked example, if only its math was untrustworthy
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
            plan, repaired, math = _parse_plan(resp.message.content or "", last_attempt=attempt == 1)
            telemetry = {
                "attempt": attempt + 1,
                "cache_hit": False,
                "prompt_tokens": resp.prompt_eval_count or 0,
                "output_tokens": resp.eval_count or 0,
                "load_sec": round((resp.load_duration or 0) / 1e9, 3),
                "eval_sec": round((resp.eval_duration or 0) / 1e9, 3),
                "total_words": total_words(plan),
                "repaired": repaired,
                "math": math,
                "fallback_used": False,
            }
            return _finish(concept, plan, telemetry, t0, use_cache)
        except LLM_ERRORS as exc:
            # Daemon down or HTTP error: there is no model output to correct, so just retry.
            errors.append(f"{type(exc).__name__}: {exc}")
            continue
        except ValidationError as exc:
            problem = _validation_feedback(exc)
        except MathCheckError as exc:
            problem = f"Math check failed: {exc}"
            salvage = getattr(exc, "salvage", None) or salvage
        errors.append(problem)
        messages.append({"role": "assistant", "content": resp.message.content or "{}"})
        messages.append({
            "role": "user",
            "content": f"{problem}\nReturn the full corrected JSON with 4-6 scenes and 18-30 words per narration.",
        })

    if salvage is not None:
        plan, repaired, math = salvage
        return _finish(concept, plan, {"attempt": 2, "cache_hit": False, "total_words": total_words(plan),
                                       "repaired": repaired, "math": math, "salvaged": True,
                                       "fallback_used": False, "errors": errors}, t0, use_cache)

    # Deterministic safe template fallback if both LLM attempts fail. Never cached, so a later run can retry the LLM.
    plan = build_safe_fallback_lesson(concept)
    return plan, {"attempt": 3, "cache_hit": False, "fallback_used": True, "total_words": total_words(plan),
                  "errors": errors, "total_sec": round(time.perf_counter() - t0, 3)}


def _finish(concept, plan, telemetry, t0, use_cache):
    telemetry["total_sec"] = round(time.perf_counter() - t0, 3)
    if use_cache:
        save_plan(concept, plan)
    return plan, telemetry
