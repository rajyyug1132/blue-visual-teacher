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
from orchestrator.mathcheck import MathCheckError, ensure_answer_spoken, verify_plan
from orchestrator.numeric_guard import NumericPolicy, audit_fields, nfkc
from orchestrator.prompts import CLASSIFY_PROMPT, FEW_SHOT_MESSAGES, QUALITATIVE_MODE, SYSTEM_PROMPT, request
from orchestrator.schema import NOT_SPOKEN, TOTAL_MAX, TOTAL_MIN, WORDS_MAX, WORDS_MIN, LessonPlan
from orchestrator.spoken import shorten_narration, to_spoken

# Primary planner: fast and resident. OLLAMA_MODEL is the older name, still honoured.
MODEL_NAME = os.environ.get("PLANNER_MODEL") or os.environ.get("OLLAMA_MODEL") or "qwen2.5:3b"
# Bigger model for one escalation attempt after the primary fails twice. PLANNER_ESCALATION_MODEL="" disables it.
ESCALATION_MODEL = os.environ.get("PLANNER_ESCALATION_MODEL", "qwen2.5:7b")
THINKING_MODEL_PREFIXES = ("qwen3", "gemma")  # only these get think=False
KEEP_ALIVE = -1  # must be a number: the string "-1" is rejected by the server ("missing unit in duration")
NUM_CTX = 4096  # same for every call: a different num_ctx makes Ollama reload the model
CLASSIFY_SCHEMA = {"type": "object", "properties": {"has_formula": {"type": "boolean"}}, "required": ["has_formula"]}

# Pinned to localhost so a stray OLLAMA_HOST can never route planning off the machine.
_client = ollama.Client(host="http://127.0.0.1:11434", timeout=120)

LLM_ERRORS = (ollama.ResponseError, ConnectionError, httpx.HTTPError)


class PlanRejected(ValueError):
    """Model output that failed a check; `problems` are fed back to the model on the next rung of the ladder.

    When every problem is a number, unit or '=' in a known string, `data` holds the parsed lesson and `patchable`
    the located issues, so the planner can rewrite just those strings instead of re-planning the whole lesson.
    """

    def __init__(self, problems: list[str], data: dict | None = None, patchable: list[dict] | None = None):
        super().__init__("; ".join(problems))
        self.problems = problems
        self.data = data
        self.patchable = patchable


# Topics that obviously have a standard formula skip the classify call (and 3b's misreads of them).
FORMULA_TOPIC = re.compile(
    r"\b(?:theorem|law|laws|interest|equation|formula|speed|velocity|acceleration|momentum|density|pressure|area"
    r"|volume|perimeter|probability|percentage|ratio|titration|molarity|ohm|voltage|resistance|current|power"
    r"|energy|force|gravitation|kinetic|potential|pythagor\w*|trigonometr\w*|quadratic|profit|discount|average"
    r"|simple interest|compound interest)\b", re.I)
PATCH_SCHEMA = {"type": "object", "properties": {"text": {"type": "string", "maxLength": 320}}, "required": ["text"]}
PATCH_RULES = {"numbers": "contains no numbers or amounts (small counts up to ten are fine)",
               "unit": "contains no units of measurement", "equals": "contains no '=' sign and no formula"}
PATCH_PROMPT = ('Rewrite this {field} from a lesson about "{concept}" so that it {rules}. Keep its meaning{length}. '
                'Plain, simple English. Reply as JSON {{"text": "..."}}.\n\n{text}')
MAX_PATCHES = 6


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
    """Keyword prior first (Pythagoras Theorem, Compound Interest...), then one tiny schema-constrained call:
    does this concept have a standard formula? Unsure or failed -> "none"."""
    if FORMULA_TOPIC.search(concept):
        return "checked"
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
    info["hook_extended"] = _extend_short_hook(data)

    math = info["math"]
    if math.get("result") is not None and not problems:
        scene = next(s for s in scenes if s.get("id") == math["scene"])
        try:
            info["answer_repaired"] = ensure_answer_spoken(scene, math["result"], math["unit"], repair_answer)
        except MathCheckError as exc:
            problems.append(str(exc))

    issues = audit_fields(data, policy, set(math.get("allowed", [])))
    try:
        plan = LessonPlan.model_validate(data)
    except ValidationError as exc:
        problems += _validation_feedback(exc)
    if problems or issues:
        # Only field-level number problems left: the caller can patch those strings instead of re-planning.
        patchable = issues if issues and not problems else None
        raise PlanRejected(problems + [i["message"] for i in issues], data=data, patchable=patchable)
    return plan, info


def _patch_fields(concept: str, rejected: PlanRejected, model: str, policy: NumericPolicy,
                  repair_answer: bool) -> tuple[LessonPlan, dict] | None:
    """Rewrite only the strings the audit flagged (one short call each), then re-run every check.

    Returns (plan, info) on success, None if the patch fails or more than MAX_PATCHES strings need it.
    The prompt states the rule only; it never offers replacement words (small models copy them verbatim).
    """
    targets: dict[tuple, set] = {}
    for issue in rejected.patchable or []:
        targets.setdefault((issue["scene_index"], issue["field"], issue["idx"]), set()).add(issue["kind"])
    if not targets or len(targets) > MAX_PATCHES:
        return None
    data = json.loads(json.dumps(rejected.data))
    for (si, field, idx), kinds in targets.items():
        scene = data["scenes"][si]
        params = scene["visual"]["params"]
        text = scene["narration"] if field == "narration" else params[field + "s"][idx]
        length = " and about the same number of words" if field == "narration" else "; under six words"
        prompt = PATCH_PROMPT.format(field="sentence" if field == "narration" else "short label", concept=concept,
                                     rules=" and ".join(PATCH_RULES[k] for k in sorted(kinds)), length=length,
                                     text=text)
        try:
            resp = _chat(model=model, messages=[{"role": "user", "content": prompt}], format=PATCH_SCHEMA,
                         keep_alive=KEEP_ALIVE, options={"temperature": 0.0, "num_ctx": NUM_CTX, "num_predict": 160})
            new = str(json.loads(resp.message.content or "{}").get("text", "")).strip()
        except (*LLM_ERRORS, ValueError):
            return None
        if not new:
            return None
        if field == "narration":
            scene["narration"] = new
        else:
            params[field + "s"][idx] = new
    try:
        return _parse_plan(json.dumps(data, ensure_ascii=False), policy, repair_answer)
    except PlanRejected:
        return None


def _extend_short_hook(data: dict) -> bool:
    """Scene 1 under WORDS_MIN words (common with 3B models) is extended from the title instead of costing a retry.

    "Why does your fan slow down in summer?" + title "Ohm's Law: Voltage and Resistance" ->
    "... in summer? Today we explore Ohm's Law, voltage and resistance." The result still goes through the
    numeric audit and schema validation, so a title with digits cannot sneak numbers in.
    """
    hook = next((s for s in data["scenes"] if s.get("id") == 1), None)
    title = data.get("title")
    if not hook or not isinstance(hook.get("narration"), str) or not isinstance(title, str):
        return False
    narration = hook["narration"].strip()
    if not narration or len(narration.split()) >= WORDS_MIN:
        return False
    topic = to_spoken(title)
    full, short = topic.replace(":", ","), topic.split(":")[0]
    for subject in (full, short):
        extended = f"{narration.rstrip()} Today we explore {subject.strip().rstrip('.')}."
        if len(extended.split()) < WORDS_MIN:
            extended += " Let's find out how it works."
        if len(extended.split()) <= WORDS_MAX:
            hook["narration"] = extended
            return True
    return False


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


def warm_up_ollama(model: str | None = None) -> None:
    """Pin model in memory at startup so live demo requests incur near-zero load_duration."""
    _client.generate(model=model or MODEL_NAME, prompt="ping", keep_alive=KEEP_ALIVE,
                     options={"num_predict": 1, "num_ctx": NUM_CTX})


def _unload(model: str) -> None:
    """keep_alive=0 evicts the model now, so only one planner model sits in VRAM (6 GB card)."""
    try:
        _client.generate(model=model, prompt="", keep_alive=0)
    except LLM_ERRORS:
        pass  # daemon down: nothing is loaded anyway


def _ladder(primary: str, escalation: str) -> list[tuple[str, str]]:
    """(stage, model) rungs before the safe template. Qualitative mode reuses whichever model is loaded last."""
    rungs = [("plan", primary), ("retry", primary)]
    if escalation and escalation != primary:
        rungs.append(("escalate", escalation))
    rungs.append(("qualitative", rungs[-1][1]))
    return rungs


def plan_lesson(concept: str, model: str | None = None, use_cache: bool = True,
                policy: NumericPolicy | None = None, escalation_model: str | None = None) -> tuple[LessonPlan, dict]:
    """Ladder: plan -> retry with the problem list -> escalate to the bigger model (fresh, with the problem list)
    -> regenerate in qualitative mode -> safe template. Telemetry records every rung's model and seconds."""
    model = model or MODEL_NAME
    escalation = ESCALATION_MODEL if escalation_model is None else escalation_model
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
    errors, rungs, problems = [], [], []
    loaded = model
    swap_sec = 0.0
    for attempt, (stage, rung_model) in enumerate(_ladder(model, escalation)):
        if rung_model != loaded:
            t_swap = time.perf_counter()
            _unload(loaded)
            swap_sec += time.perf_counter() - t_swap
            loaded = rung_model
        stage_policy: NumericPolicy = "none" if stage == "qualitative" else policy
        if stage == "escalate":
            # Fresh conversation for the bigger model, told what went wrong (no drafts to copy from).
            note = ("\nA previous draft was rejected for these problems; avoid them:\n- " + "\n- ".join(problems)
                    if problems else "")
            messages = base + [{"role": "user", "content": request(concept, policy) + note}]
        elif stage == "qualitative":
            # Fresh conversation: the failed drafts would pull the model back to the same numbers.
            messages = base + [{"role": "user", "content": request(concept, "none") + "\n" + QUALITATIVE_MODE}]
        resp = None
        t_rung = time.perf_counter()
        try:
            resp = _chat(
                model=rung_model,
                messages=messages,
                format=LessonPlan.model_json_schema(),
                keep_alive=KEEP_ALIVE,
                options={"temperature": 0.0 if stage in ("plan", "escalate") else 0.2, "num_ctx": NUM_CTX,
                         "num_predict": 850},
            )
            plan, info = _parse_plan(resp.message.content or "", stage_policy, repair_answer=stage != "plan")
            rungs.append({"stage": stage, "model": rung_model, "sec": round(time.perf_counter() - t_rung, 2),
                          "ok": True})
            telemetry = {
                "attempt": attempt + 1,
                "stage": stage,
                "model": rung_model,
                "cache_hit": False,
                "classify_sec": classify_sec,
                "prompt_tokens": resp.prompt_eval_count or 0,
                "output_tokens": resp.eval_count or 0,
                "load_sec": round((resp.load_duration or 0) / 1e9, 3),
                "eval_sec": round((resp.eval_duration or 0) / 1e9, 3),
                "total_words": total_words(plan),
                "fallback_used": False,
                "errors": errors,
                "rungs": rungs,
                **info,
            }
            return _finish(concept, plan, telemetry, t0, use_cache, model, loaded, swap_sec)
        except LLM_ERRORS as exc:
            # Daemon down or HTTP error: there is no model output to correct, so go to the next rung.
            errors.append(f"{stage}: {type(exc).__name__}: {exc}")
            rungs.append({"stage": stage, "model": rung_model, "sec": round(time.perf_counter() - t_rung, 2),
                          "ok": False})
            continue
        except PlanRejected as exc:
            problems = exc.problems
            errors.append(f"{stage}: " + " | ".join(exc.problems))
            if exc.patchable and stage != "qualitative":
                patched = _patch_fields(concept, exc, rung_model, stage_policy, repair_answer=stage != "plan")
                if patched:
                    plan, info = patched
                    rungs.append({"stage": stage + "+patch", "model": rung_model,
                                  "sec": round(time.perf_counter() - t_rung, 2), "ok": True,
                                  "patched": len({(i["scene_index"], i["field"], i["idx"]) for i in exc.patchable})})
                    telemetry = {"attempt": attempt + 1, "stage": stage + "+patch", "model": rung_model,
                                 "cache_hit": False, "classify_sec": classify_sec,
                                 "total_words": total_words(plan), "fallback_used": False, "errors": errors,
                                 "rungs": rungs, **info}
                    return _finish(concept, plan, telemetry, t0, use_cache, model, loaded, swap_sec)
            rungs.append({"stage": stage, "model": rung_model, "sec": round(time.perf_counter() - t_rung, 2),
                          "ok": False})
            feedback = "Problems:\n- " + "\n- ".join(exc.problems)
        messages = messages + [
            {"role": "assistant", "content": resp.message.content or "{}"},
            {"role": "user", "content": f"{feedback}\nReturn the full corrected JSON with 4-6 scenes and 18-30 "
                                        "words per narration."},
        ]

    # Deterministic safe template if every rung failed. Never cached, so a later run can retry the LLM.
    plan = build_safe_fallback_lesson(concept)
    telemetry = {"attempt": len(rungs) + 1, "stage": "template", "model": None, "cache_hit": False,
                 "fallback_used": True, "policy": policy, "classify_sec": classify_sec,
                 "total_words": total_words(plan), "math": {"status": "none"}, "errors": errors, "rungs": rungs}
    return _finish(concept, plan, telemetry, t0, False, model, loaded, swap_sec)


def _finish(concept, plan, telemetry, t0, use_cache, primary, loaded, swap_sec):
    telemetry["total_sec"] = round(time.perf_counter() - t0, 3)  # time the student waited for this plan
    if loaded != primary:
        # Put the fast model back for the next request; this runs after the plan is ready.
        t_swap = time.perf_counter()
        _unload(loaded)
        try:
            warm_up_ollama(primary)
        except LLM_ERRORS:
            pass
        swap_sec += time.perf_counter() - t_swap
    telemetry["swap_sec"] = round(swap_sec, 2)
    if use_cache:
        save_plan(concept, plan)
    return plan, telemetry
