# orchestrator/planner.py
import json
import os
import time

import httpx
import ollama
from pydantic import ValidationError

from orchestrator.cache import load_plan, save_plan
from orchestrator.fallbacks import build_safe_fallback_lesson
from orchestrator.mathcheck import MathCheckError, ensure_answer_spoken, verify_plan
from orchestrator.numeric_guard import NumericPolicy, audit_numbers, nfkc
from orchestrator.prompts import CLASSIFY_PROMPT, FEW_SHOT_MESSAGES, QUALITATIVE_MODE, SYSTEM_PROMPT, request
from orchestrator.schema import NOT_SPOKEN, TOTAL_MAX, TOTAL_MIN, WORDS_MAX, LessonPlan
from orchestrator.spoken import shorten_narration, to_spoken

MODEL_NAME = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")  # GPU gets the planner; TTS/MT run on CPU (DEVICE)
THINKING_MODEL_PREFIXES = ("qwen3", "gemma")  # only these get think=False
KEEP_ALIVE = -1  # must be a number: the string "-1" is rejected by the server ("missing unit in duration")
NUM_CTX = 4096  # same for every call: a different num_ctx makes Ollama reload the model
CLASSIFY_SCHEMA = {"type": "object", "properties": {"has_formula": {"type": "boolean"}}, "required": ["has_formula"]}
STAGES = ("plan", "retry", "qualitative")  # then the safe template

# Pinned to localhost so a stray OLLAMA_HOST can never route planning off the machine.
_client = ollama.Client(host="http://127.0.0.1:11434", timeout=120)

LLM_ERRORS = (ollama.ResponseError, ConnectionError, httpx.HTTPError)


class PlanRejected(ValueError):
    """Model output that failed a check; `problems` are fed back to the model on the next rung of the ladder."""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


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


def classify_topic(concept: str, model: str = MODEL_NAME) -> NumericPolicy:
    """One tiny schema-constrained call: does this concept have a standard formula? Unsure or failed -> "none"."""
    try:
        resp = _chat(model=model, messages=[{"role": "user", "content": CLASSIFY_PROMPT.format(concept=concept.strip())}],
                     format=CLASSIFY_SCHEMA, keep_alive=KEEP_ALIVE,
                     options={"temperature": 0.0, "num_ctx": NUM_CTX, "num_predict": 16})
        return "checked" if json.loads(resp.message.content or "{}").get("has_formula") is True else "none"
    except (*LLM_ERRORS, ValueError):
        return "none"  # making no numeric claims is the safe side


def _parse_plan(content: str, policy: NumericPolicy, repair_answer: bool) -> tuple[LessonPlan, dict]:
    """parse -> verify math (digits still present) -> spoken words -> trim -> spoken answer -> audit -> schema.

    Returns (plan, info). Raises PlanRejected with every problem found, for the next rung of the ladder.
    """
    try:
        data = json.loads(content)
        scenes = data["scenes"]
        assert isinstance(scenes, list) and all(isinstance(s, dict) for s in scenes)
    except (ValueError, KeyError, TypeError, AssertionError):
        try:
            LessonPlan.model_validate_json(content)
        except ValidationError as exc:
            raise PlanRejected(_validation_feedback(exc)) from None
        raise PlanRejected(["JSON: scenes must be a list of objects"]) from None

    info = {"policy": policy, "math": {"status": "none"}, "repaired": False, "answer_repaired": False}
    problems = []
    if policy == "none":
        for scene in scenes:
            scene["check"] = None  # nothing to verify in a descriptive topic; the audit rejects any numbers
    else:
        try:
            info["math"] = verify_plan(data)
        except MathCheckError as exc:
            problems.append(f"Math check failed: {exc}")
        except (KeyError, TypeError, AttributeError):
            info["math"] = {"status": "unchecked"}  # malformed scene; schema validation reports it

    for scene in scenes:
        narration = scene.get("narration")
        if not isinstance(narration, str):
            continue
        if NOT_SPOKEN.search(nfkc(narration)):
            narration = to_spoken(narration)  # spelling out can add words, so trim after
        if len(narration.split()) > WORDS_MAX:
            narration = shorten_narration(narration) or narration
        info["repaired"] |= narration != scene["narration"]
        scene["narration"] = narration

    math = info["math"]
    if math.get("result") is not None and not problems:
        scene = next(s for s in scenes if s.get("id") == math["scene"])
        try:
            info["answer_repaired"] = ensure_answer_spoken(scene, math["result"], math["unit"], repair_answer)
        except MathCheckError as exc:
            problems.append(str(exc))

    problems += audit_numbers(data, policy, set(math.get("allowed", [])))
    try:
        plan = LessonPlan.model_validate(data)
    except ValidationError as exc:
        problems += _validation_feedback(exc)
    if problems:
        raise PlanRejected(problems)
    return plan, info


def _validation_feedback(exc: ValidationError) -> list[str]:
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
    return lines


def warm_up_ollama(model: str = MODEL_NAME) -> None:
    """Pin model in memory at startup so live demo requests incur near-zero load_duration."""
    _client.generate(model=model, prompt="ping", keep_alive=KEEP_ALIVE, options={"num_predict": 1, "num_ctx": NUM_CTX})


def plan_lesson(concept: str, model: str = MODEL_NAME, use_cache: bool = True,
                policy: NumericPolicy | None = None) -> tuple[LessonPlan, dict]:
    """Retry ladder: plan -> retry with the problem list -> regenerate in qualitative mode -> safe template."""
    t0 = time.perf_counter()
    if use_cache and (cached := load_plan(concept)) is not None:
        return cached, {"cache_hit": True, "fallback_used": False, "total_words": total_words(cached),
                        "total_sec": round(time.perf_counter() - t0, 4)}

    t_classify = time.perf_counter()
    if policy is None:
        policy = classify_topic(concept, model)
    classify_sec = round(time.perf_counter() - t_classify, 3)

    base = [{"role": "system", "content": SYSTEM_PROMPT}] + FEW_SHOT_MESSAGES
    messages = base + [{"role": "user", "content": request(concept, policy)}]
    errors = []
    for attempt, stage in enumerate(STAGES):
        stage_policy: NumericPolicy = "none" if stage == "qualitative" else policy
        if stage == "qualitative":
            # Fresh conversation: the failed drafts would pull the model back to the same numbers.
            messages = base + [{"role": "user", "content": request(concept, "none") + "\n" + QUALITATIVE_MODE}]
        resp = None
        try:
            resp = _chat(
                model=model,
                messages=messages,
                format=LessonPlan.model_json_schema(),
                keep_alive=KEEP_ALIVE,
                options={"temperature": 0.0 if attempt == 0 else 0.2, "num_ctx": NUM_CTX, "num_predict": 850},
            )
            plan, info = _parse_plan(resp.message.content or "", stage_policy, repair_answer=stage != "plan")
            telemetry = {
                "attempt": attempt + 1,
                "stage": stage,
                "cache_hit": False,
                "classify_sec": classify_sec,
                "prompt_tokens": resp.prompt_eval_count or 0,
                "output_tokens": resp.eval_count or 0,
                "load_sec": round((resp.load_duration or 0) / 1e9, 3),
                "eval_sec": round((resp.eval_duration or 0) / 1e9, 3),
                "total_words": total_words(plan),
                "fallback_used": False,
                "errors": errors,
                **info,
            }
            return _finish(concept, plan, telemetry, t0, use_cache)
        except LLM_ERRORS as exc:
            # Daemon down or HTTP error: there is no model output to correct, so go to the next rung.
            errors.append(f"{stage}: {type(exc).__name__}: {exc}")
            continue
        except PlanRejected as exc:
            errors.append(f"{stage}: " + " | ".join(exc.problems))
            feedback = "Problems:\n- " + "\n- ".join(exc.problems)
        messages = messages + [
            {"role": "assistant", "content": resp.message.content or "{}"},
            {"role": "user", "content": f"{feedback}\nReturn the full corrected JSON with 4-6 scenes and 18-30 "
                                        "words per narration."},
        ]

    # Deterministic safe template if every rung failed. Never cached, so a later run can retry the LLM.
    plan = build_safe_fallback_lesson(concept)
    return plan, {"attempt": len(STAGES) + 1, "stage": "template", "cache_hit": False, "fallback_used": True,
                  "policy": policy, "classify_sec": classify_sec, "total_words": total_words(plan),
                  "math": {"status": "none"}, "errors": errors, "total_sec": round(time.perf_counter() - t0, 3)}


def _finish(concept, plan, telemetry, t0, use_cache):
    telemetry["total_sec"] = round(time.perf_counter() - t0, 3)
    if use_cache:
        save_plan(concept, plan)
    return plan, telemetry
