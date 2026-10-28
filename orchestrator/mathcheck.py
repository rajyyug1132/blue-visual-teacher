# orchestrator/mathcheck.py — verify worked-example arithmetic before narration is spelled out.
# Runs on the raw JSON dict (digits still present): parse -> verify -> to_spoken -> trim -> answer -> audit -> schema.
import ast
import operator
import re

from orchestrator.numeric_guard import (SUPERSCRIPT, close, digit_number_spans, in_allowed, is_small_int, nfkc,
                                        spoken_number_spans, spoken_numbers)
from orchestrator.schema import WORDS_MAX
from orchestrator.spoken import shorten_narration, to_spoken

TOLERANCE = 0.005  # +-0.5 %
MAX_EXPONENT = 100
MAX_MAGNITUDE = 1e12
VARIABLE_SIDE = re.compile(r"\s*[A-Za-z][A-Za-z_]*\s*(?:[²³]|\^\s*\d)?\s*")

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}
NUMBER = re.compile(r"\d+(?:,\d{2,3})*(?:\.\d+)?")
# A number standing where an answer is stated: "= 5", "gives five", "you'll have about 130,000", "is Rs. 6".
RESULT_CUE = re.compile(
    r"(?:=|\b(?:equals|gives|give|is|are|was|were|becomes?|makes?|gets?|have|has|totals?|grows to|comes to"
    r"|rises to|amounts to))\s*(?:(?:about|exactly|approximately|roughly|nearly|only|just)\s+)*"
    r"(?:rs\.?\s*|₹\s*|\$\s*)?$", re.I)
UNIT_NAMES = {"a": "amperes", "amp": "amperes", "amps": "amperes", "v": "volts", "Ω": "ohms", "ohm": "ohms",
              "%": "percent", "rs": "rupees", "rs.": "rupees", "₹": "rupees", "inr": "rupees", "$": "dollars",
              "n": "newtons", "m": "metres", "km": "kilometres", "kg": "kilograms", "g": "grams", "j": "joules",
              "w": "watts", "s": "seconds", "m/s": "metres per second", "km/h": "kilometres per hour"}


class MathCheckError(ValueError):
    """The plan's arithmetic cannot be trusted; the message is fed back to the LLM on retry."""


def safe_eval(expr: str) -> float:
    """Evaluate arithmetic with an AST whitelist. Never eval(): names, calls and attributes are rejected."""
    # "c² = 6² + 8²" or "100 = 36 + 64": evaluate every side that is pure arithmetic; they must agree.
    sides = []
    for part in expr.split("="):
        try:
            sides.append((bool(re.search(r"[-+*/×÷^√²³]|\bsqrt\b", part.strip().lstrip("-"))), _eval_side(part, expr)))
        except MathCheckError:
            if not VARIABLE_SIDE.fullmatch(part):  # only a bare symbol like "c²" or "A" may be skipped
                raise
    if not any(has_op for has_op, _ in sides):
        raise MathCheckError(f"check.expr {expr!r} must contain the calculation itself, not just its answer")
    values = [v for _, v in sides]
    if any(abs(v - values[0]) > 1e-6 * max(abs(v), abs(values[0]), 1) for v in values):
        raise MathCheckError(f"check.expr {expr!r}: the two sides of '=' do not agree")
    return next((v for has_op, v in reversed(sides) if has_op), values[0])


def _eval_side(part: str, expr: str) -> float:
    # Powers written as superscripts must become ** before anything else: NFKC would turn 6² into "62".
    text = re.sub(r"([⁰¹²³⁴⁵⁶⁷⁸⁹]+)", lambda m: "**" + m.group(1).translate(SUPERSCRIPT), part)
    text = re.sub(r"\bsqrt\s*\(", "√(", text)  # models write sqrt(9 + 16) as often as √(9 + 16)
    text = re.sub(r"√\s*(\d+(?:\.\d+)?|\([^()]*\))", r"(\1)**0.5", text)  # √100, √(36 + 64)
    text = text.replace("×", "*").replace("÷", "/").replace("^", "**").strip()
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)  # 10,000 -> 10000
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise MathCheckError(f"check.expr {expr!r} is not valid arithmetic") from exc

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            return OPS[type(node.op)](walk(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Pow) and (abs(right) > MAX_EXPONENT or abs(left) > 1e6):
                raise MathCheckError(f"check.expr {expr!r}: power too large")
            if isinstance(node.op, ast.Div) and right == 0:
                raise MathCheckError(f"check.expr {expr!r}: division by zero")
            value = OPS[type(node.op)](left, right)
            if isinstance(value, complex) or abs(value) > MAX_MAGNITUDE:
                raise MathCheckError(f"check.expr {expr!r}: result out of range")
            return value
        raise MathCheckError(f"check.expr {expr!r} may only use numbers, + - * / ** and parentheses")

    try:
        return float(walk(tree))
    except OverflowError as exc:  # e.g. 1e6 ** 100 on floats
        raise MathCheckError(f"check.expr {expr!r}: result out of range") from exc


def _first_number(text: str) -> tuple[str, float] | None:
    m = NUMBER.search(text)
    return (m.group(0), float(m.group(0).replace(",", ""))) if m else None


def _fmt(value: float) -> str:
    return str(int(round(value))) if abs(value - round(value)) < 1e-9 else f"{value:.2f}"


def _for_speech(value: float) -> str:
    """Narration wording for a corrected value: 128203.72 -> "about 128000", so it stays short when spoken."""
    if abs(value) < 1000:
        return _fmt(value)
    rounded = float(f"{value:.3g}")
    return _fmt(rounded) if rounded == value else f"about {_fmt(rounded)}"


def _off(computed: float, claimed: float) -> bool:
    return abs(computed - claimed) > TOLERANCE * max(abs(computed), 1e-9)


def replace_result(text: str, wrong: float, right: str, spoken: bool = False) -> str:
    """Replace the wrong value only where it is stated as a result, never globally.

    Spans are found first (digits, plus spelled-out numbers when `spoken`), kept only if a result cue
    ("=", "gives", "is", ...) comes right before them, then edited right-to-left so earlier offsets stay valid.
    "At 5% interest the gain is 5" with wrong=5 changes only the second 5.
    """
    spans = digit_number_spans(text) + (spoken_number_spans(text) if spoken else [])
    edits = sorted({(s, e) for v, s, e in spans if close(v, wrong, 1e-9) and RESULT_CUE.search(text[:s])},
                   reverse=True)
    for s, e in edits:
        rep = right
        if rep.startswith("about ") and re.search(r"\b(?:about|approximately|roughly|nearly)\s*$", text[:s], re.I):
            rep = rep[len("about "):]
        text = text[:s] + rep + text[e:]
    return text


def _check_steps(texts: list[str]) -> tuple[dict[float, float], set[float]]:
    """Labels/steps shaped "<arithmetic> = <number>": (wrong shown value -> right value, numbers that verified).

    Units are stripped and "5%" read as 5/100 before evaluating ("230 V ÷ 46 Ω = 5 A" -> 230 ÷ 46). Inputs like
    "P = 100,000" have no arithmetic on the left and are skipped, as is anything that doesn't parse.
    """
    fixes, verified = {}, set()
    for text in texts:
        left, eq, right = text.rpartition("=")
        shown = _first_number(right) if eq else None
        if shown is None or not re.search(r"[\d²³]\s*%?\s*[×÷*/+^-]|√", left):
            continue
        left = re.sub(r"^.*:", "", left)  # "Formula: 230 / 46"
        expr = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", left)
        try:
            value = safe_eval(re.sub(r"[A-Za-zΩ₹$]+", " ", expr))
        except MathCheckError:
            continue
        verified |= {v for v, _, _ in digit_number_spans(left)} | {value}
        if _off(value, shown[1]):
            fixes[shown[1]] = value
    return fixes, verified


def unit_words(result: str) -> str:
    """Spoken unit of a check.result: "5 A" -> "amperes", "Rs. 6" -> "rupees", "5" -> ""."""
    num = _first_number(result)
    rest = (result.replace(num[0], " ", 1) if num else result).strip()
    if not rest:
        return ""
    if rest.lower() in UNIT_NAMES or rest in UNIT_NAMES:
        return UNIT_NAMES.get(rest.lower(), UNIT_NAMES.get(rest, ""))
    words = to_spoken(rest)
    return words if re.fullmatch(r"[A-Za-z ]+", words) else ""


def verify_plan(data: dict) -> dict:
    """Check every scene's check.expr; fix wrong results in place, at their result positions only.

    Returns {"status": none|ok|fixed, "result", "unit", "scene", "allowed": numbers the audit may accept}.
    Raises MathCheckError when the arithmetic can't be verified so the planner can retry.
    """
    report = {"status": "none", "allowed": []}
    allowed = set()
    for scene in data.get("scenes", []):
        check = scene.get("check")
        if not check:
            continue
        computed = safe_eval(str(check.get("expr", "")))
        claimed = _first_number(str(check.get("result", "")))
        if claimed is None:  # small models often spell the answer out ("eight"); read it as the narration says it
            spelled = spoken_numbers(str(check.get("result", "")))
            claimed = (str(check.get("result", "")), spelled[0]) if spelled else None
        if claimed is None:
            raise MathCheckError(f"Scene {scene.get('id')} check.result {check.get('result')!r} has no number")
        params = scene["visual"]["params"]
        _require_numbers_in_scene(scene, check["expr"])
        # The model may also show a different (wrong) answer on screen than in check.result, e.g.
        # step "100,000 × (1 + 0.05/4)^(4×5) = 130,000" with result "134,685.50": check each step on its own too.
        fixes, verified = _check_steps(params.get("labels", []) + params.get("steps", []))
        if _off(computed, claimed[1]):
            fixes[claimed[1]] = computed
        for wrong, value in fixes.items():
            scene["narration"] = replace_result(scene["narration"], wrong, _for_speech(value), spoken=True)
            params["labels"] = [replace_result(s, wrong, _fmt(value)) for s in params.get("labels", [])]
            params["steps"] = [replace_result(s, wrong, _fmt(value)) for s in params.get("steps", [])]
        if claimed[1] in fixes:
            check["result"] = check["result"].replace(claimed[0], _fmt(fixes[claimed[1]]), 1)
        allowed |= {v for v, _, _ in digit_number_spans(check["expr"])} | verified | set(fixes.values()) | {computed}
        report = {"status": "fixed" if fixes else "ok", "scene": scene.get("id"), "expr": check["expr"],
                  "claimed": claimed[1], "computed": round(computed, 4), "result": computed,
                  "unit": unit_words(check["result"])}
    report["allowed"] = sorted(allowed)
    return report


def ensure_answer_spoken(scene: dict, value: float, unit: str, repair: bool) -> bool:
    """The worked example must say its verified answer out loud. Narration is already spelled out here.

    Returns True if it had to be repaired. Without `repair`, raises MathCheckError (the planner retries once);
    with it, appends "So the answer is ..." and trims earlier clauses to stay within the word limit.
    """
    if any(close(v, value) for v in spoken_numbers(scene["narration"])):
        return False
    sentence = f"So the answer is {to_spoken(_for_speech(value))}{' ' + unit if unit else ''}."
    if not repair:
        raise MathCheckError(f"Scene {scene.get('id')}: narration must say the final answer, "
                             f"{sentence[len('So the answer is '):-1]}.")
    budget = WORDS_MAX - len(sentence.split())
    body = scene["narration"]
    if len(body.split()) > budget:
        body = shorten_narration(body, max_words=budget)
        if body is None:  # never swap the example for generic filler: let the ladder move to its next rung
            raise MathCheckError(f"Scene {scene.get('id')}: narration must say the final answer, "
                                 f"{sentence[len('So the answer is '):-1]}, within {WORDS_MAX} words.")
    scene["narration"] = f"{body} {sentence}"
    return True


def _require_numbers_in_scene(scene: dict, expr: str) -> None:
    """A check must compute this scene's example: its numbers (beyond small counts) must be shown or spoken here.

    Rejects checks copied from elsewhere, e.g. Ohm's Law "230 / 46" on a titration scene. Rates may appear either
    way round ("0.05" in the check, "5%" or "five percent" in the scene).
    """
    params = scene.get("visual", {}).get("params", {})
    shown = " ".join(params.get("labels", []) + params.get("steps", []) + [scene.get("narration", "")])
    present = {v for v, _, _ in digit_number_spans(nfkc(shown))} | set(spoken_numbers(scene.get("narration", "")))
    if re.search(r"%|percent", shown, re.I):
        present.add(100.0)  # "5 / 100" is how a percentage is computed
    missing = [v for v, _, _ in digit_number_spans(expr) if not is_small_int(v) and not in_allowed(v, present)]
    if missing:
        nums = ", ".join(_fmt(v) for v in missing)
        raise MathCheckError(f"Scene {scene.get('id')} check.expr uses {nums}, which this scene never shows or says. "
                             "The check must compute the example this scene teaches.")
