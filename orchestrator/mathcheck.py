# orchestrator/mathcheck.py — verify worked-example arithmetic before narration is spelled out.
# Runs on the raw JSON dict (digits still present): parse -> verify -> to_spoken -> trim -> schema validate.
import ast
import operator
import re

from orchestrator.spoken import to_spoken

TOLERANCE = 0.005  # +-0.5 %
MAX_EXPONENT = 100
MAX_MAGNITUDE = 1e12
WORKED_EXAMPLE_ID = 4

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}
NUMBER = re.compile(r"\d+(?:,\d{2,3})*(?:\.\d+)?")
LIST_PREFIX = re.compile(r"^\s*(?:step\s*)?\d+\s*[.:)]\s*", re.I)  # "Step 1:", "2." are numbering, not quantities
YEAR = re.compile(r"\b1\d{3}\b|\b20\d{2}\b")
NUMBER_WORDS = re.compile(
    r"\b(?:hundred|thousand|million|billion|lakh|crore|percent|eleven|twelve|\w+teen|twenty|thirty|forty|fifty"
    r"|sixty|seventy|eighty|ninety)\b", re.I)
# "V = I × R", "A = P(1 + r/n)^nt", "F = ma": a short symbol equal to an expression with a variable in it.
# "Rainfall = 200 mm" or "Total = 200000" is a computed label, not a formula.
FORMULA = re.compile(r"(?<![\w.])[A-Za-z][A-Za-z₀-₉_]{0,2}\s*=\s*[^=]*?(?<![A-Za-z])[A-Za-z]{1,2}(?![A-Za-z])")
# A computed or produced amount, as opposed to data being walked through (a sorted list, a year, a step number).
ARITHMETIC_WORDS = re.compile(
    r"\b(?:times|multipl\w*|divid\w*|plus|minus|percent|equals?|gives?|giving|produces?|makes?|results?\s+in"
    r"|totals?|sum|product|interest|amount|costs?|earns?|grows?\s+to|you\s+get|we\s+get|you'll\s+have)\b", re.I)

QUALITATIVE_NARRATION = ("Let's walk through it step by step: start from what we already know, apply the rule from "
                         "the previous scene, and check that the result makes sense.")
QUALITATIVE_PARAMS = {"labels": ["Start from what we know", "Apply the rule", "Check the result"],
                      "steps": ["First, list what is given", "Then, apply the rule", "Finally, check it makes sense"]}


class MathCheckError(ValueError):
    """The plan's arithmetic cannot be trusted; the message is fed back to the LLM on retry."""


def safe_eval(expr: str) -> float:
    """Evaluate arithmetic with an AST whitelist. Never eval(): names, calls and attributes are rejected."""
    text = expr.replace("×", "*").replace("÷", "/").replace("^", "**")
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


def _replace_number(text: str, wrong: float, right: str) -> str:
    """Swap every occurrence of the wrong value, as digits or as spelled-out words, for the right one."""
    out = NUMBER.sub(lambda m: right if abs(float(m.group(0).replace(",", "")) - wrong) < 1e-9 else m.group(0), text)
    wrong_words = to_spoken(_fmt(wrong))
    # Whole spoken numbers only: "five" must not match inside "twenty-five" or "five hundred".
    pattern = rf"(?<![\w-]){re.escape(wrong_words)}(?![\w-]| hundred| thousand| million| point)"
    return re.sub(pattern, to_spoken(right), out)


def _states_a_computed_amount(scene: dict) -> bool:
    """Numbers (digits anywhere, or number words in narration) plus arithmetic/result language in narration.

    Symbols in labels don't count: data walkthroughs show comparisons like "Mid = 50 (< 72)".
    """
    narration = scene.get("narration", "")
    params = scene.get("visual", {}).get("params", {})
    shown = [LIST_PREFIX.sub("", s) for s in params.get("labels", []) + params.get("steps", [])]
    text = YEAR.sub("", " ".join([narration] + shown))
    has_numbers = bool(re.search(r"\d", text) or NUMBER_WORDS.search(narration))
    return has_numbers and bool(ARITHMETIC_WORDS.search(narration))


def verify_plan(data: dict) -> dict:
    """Check every scene's check.expr against check.result; fix wrong numbers in place.

    Returns telemetry {"status": none|ok|fixed, ...}. Raises MathCheckError when the arithmetic can't be
    verified (bad expr, or a worked example with quantities but no check) so the planner can retry.
    """
    report = {"status": "none"}
    shown = [t for s in data.get("scenes", []) for t in s["visual"]["params"].get("labels", [])
             + s["visual"]["params"].get("steps", [])]
    has_formula = any(FORMULA.search(t) for t in shown)
    for scene in data.get("scenes", []):
        check = scene.get("check")
        if not has_formula and (check or (scene.get("id") == WORKED_EXAMPLE_ID and _states_a_computed_amount(scene))):
            raise MathCheckError(
                f"Scene {scene.get('id')} calculates with numbers, but this topic has no formula. Do not invent "
                "quantities or measurements: remove \"check\" and walk through the steps in words.")
        if not check:
            if scene.get("id") == WORKED_EXAMPLE_ID and _states_a_computed_amount(scene):
                raise MathCheckError(
                    f"Scene {WORKED_EXAMPLE_ID} computes an amount but has no check. Either add "
                    '"check": {"expr": "<arithmetic>", "result": "<answer>"} or remove the invented quantities '
                    "and explain the steps in words.")
            continue
        computed = safe_eval(str(check.get("expr", "")))
        claimed = _first_number(str(check.get("result", "")))
        if claimed is None:
            raise MathCheckError(f"Scene {scene.get('id')} check.result {check.get('result')!r} has no number")
        params = scene["visual"]["params"]
        # The model may also show a different (wrong) answer on screen than in check.result, e.g.
        # step "100,000 × (1 + 0.05/4)^(4×5) = 130,000" with result "134,685.50": check each step on its own too.
        fixes = {}  # wrong value -> right value
        if _off(computed, claimed[1]):
            fixes[claimed[1]] = computed
        fixes.update(_wrong_steps(params.get("labels", []) + params.get("steps", [])))
        report = {"status": "fixed" if fixes else "ok", "scene": scene.get("id"), "expr": check["expr"],
                  "claimed": claimed[1], "computed": round(computed, 4)}
        for wrong, value in fixes.items():
            right = _fmt(value)
            scene["narration"] = _replace_number(scene["narration"], wrong, _for_speech(value))
            params["labels"] = [_replace_number(s, wrong, right) for s in params.get("labels", [])]
            params["steps"] = [_replace_number(s, wrong, right) for s in params.get("steps", [])]
        if claimed[1] in fixes:
            check["result"] = check["result"].replace(claimed[0], _fmt(fixes[claimed[1]]), 1)
    return report


def _off(computed: float, claimed: float) -> bool:
    return abs(computed - claimed) > TOLERANCE * max(abs(computed), 1e-9)


def _wrong_steps(texts: list[str]) -> dict[float, float]:
    """Labels/steps shaped "<arithmetic> = <number>" whose arithmetic disagrees with the number shown.

    Units are stripped before evaluating ("230 V ÷ 46 Ω = 5 A" -> 230 ÷ 46). Inputs like "P = 100,000" have no
    arithmetic on the left and are skipped, as is anything that doesn't parse.
    """
    wrong = {}
    for text in texts:
        left, eq, right = text.rpartition("=")
        shown = _first_number(right) if eq else None
        if shown is None or not re.search(r"\d\s*[×÷*/+^-]", left):
            continue
        left = re.sub(r"^.*:", "", left)  # "Formula: 230 / 46"
        try:
            value = safe_eval(re.sub(r"[A-Za-zΩ%₹$]+", " ", left))
        except MathCheckError:
            continue
        if _off(value, shown[1]):
            wrong[shown[1]] = value
    return wrong


def make_qualitative(data: dict) -> dict:
    """Last resort after a failed retry: drop the worked example's numbers and walk through the steps in words."""
    for scene in data.get("scenes", []):
        if scene.get("id") == WORKED_EXAMPLE_ID or scene.get("check"):
            scene["narration"] = QUALITATIVE_NARRATION
            scene["visual"] = {"type": "flow", "params": {k: list(v) for k, v in QUALITATIVE_PARAMS.items()}}
            scene["check"] = None
    return {"status": "template"}
