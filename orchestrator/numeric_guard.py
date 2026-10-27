# orchestrator/numeric_guard.py — which numbers a lesson may contain, read from narration, labels and steps.
#
# NumericPolicy (decided once per topic by a tiny classify call in planner.py):
#   none    descriptive topic (Monsoon, Mughal Empire): no quantities at all. No digits, no number words above ten,
#           no units of measurement and no "=" in narration, labels or steps.
#   checked quantitative topic (Ohm's Law, Compound Interest): every number must come from the arithmetic-checked
#           worked example (check.expr, its result, and steps whose arithmetic verifies). Integers up to ten are
#           exempt everywhere: "three takeaways", "step two".
import re
import unicodedata
from typing import Literal

NumericPolicy = Literal["none", "checked"]

SMALL_INT_MAX = 10
MATCH_TOLERANCE = 0.01  # spoken values are rounded ("about one hundred twenty-eight thousand")

UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
BIG = {"thousand": 10**3, "lakh": 10**5, "million": 10**6, "crore": 10**7, "billion": 10**9}

DIGIT_NUMBER = re.compile(r"\d+(?:,\d{2,3})*(?:\.\d+)?")
LIST_PREFIX = re.compile(r"^\s*(?:step\s*)?\d+\s*[.:)]\s*", re.I)  # "Step 1:", "2." are numbering, not quantities
UNIT_WORDS = re.compile(
    r"\b(?:per\s*cent|percent(?:age)?|degrees?|celsius|fahrenheit|kelvin|(?:kilo|centi|milli)?(?:metres?|meters?)"
    r"|km|cm|mm|kg|mg|ml|(?:kilo|milli)?grams?|tonnes?|tons?|(?:milli)?lit(?:re|er)s?|hectares?|acres?"
    r"|kilometres?|kilometers?|miles?|feet|foot|inches?|volts|amperes?|amps|ohms|watts|joules|newtons|pascals?"
    r"|calories?|rupees|dollars|kmph|mph)\b", re.I)


def nfkc(text: str) -> str:
    """CO₂ -> CO2, km² -> km2: compatibility forms become plain digits so the digit rules can see them."""
    return unicodedata.normalize("NFKC", text)


def spoken_number_spans(text: str) -> list[tuple[float, int, int]]:
    """Numbers written as words, with their character spans: "fifty-five degrees" -> [(55, 0, 10)]."""
    toks = [(m.group(0), m.start(), m.end()) for m in re.finditer(r"[a-z]+", text.lower())]
    out = []
    total = cur = 0
    start = end = None
    active = False

    def flush():
        nonlocal total, cur, active, start, end
        if active:
            out.append((float(total + cur), start, end))
        total = cur = 0
        active = False
        start = end = None

    i = 0
    while i < len(toks):
        w, s, e = toks[i]
        if w in UNITS or w in TENS:
            if not active:
                start = s
            cur += UNITS.get(w, TENS.get(w))
            active, end = True, e
        elif w == "hundred" and active:
            cur, end = (cur or 1) * 100, e
        elif w in BIG and active:
            total, cur, end = total + (cur or 1) * BIG[w], 0, e
        elif w == "point" and active:
            j, frac = i + 1, ""
            while j < len(toks) and toks[j][0] in UNITS and UNITS[toks[j][0]] < 10:
                frac += str(UNITS[toks[j][0]])
                end = toks[j][2]
                j += 1
            if frac:
                out.append((total + cur + float("0." + frac), start, end))
                total = cur = 0
                active = False
                i = j
                continue
            flush()
        elif w == "and" and active:
            pass
        else:
            flush()
        i += 1
    flush()
    return out


def spoken_numbers(text: str) -> list[float]:
    return [v for v, _, _ in spoken_number_spans(nfkc(text))]


def digit_number_spans(text: str) -> list[tuple[float, int, int]]:
    return [(float(m.group(0).replace(",", "")), m.start(), m.end()) for m in DIGIT_NUMBER.finditer(text)]


def is_small_int(value: float) -> bool:
    return value == int(value) and 0 <= value <= SMALL_INT_MAX


def close(a: float, b: float, tol: float = MATCH_TOLERANCE) -> bool:
    return abs(a - b) <= tol * max(abs(a), abs(b), 1e-9)


def in_allowed(value: float, allowed: set[float]) -> bool:
    """Allowed as-is, or as the same rate written the other way ("five percent" vs 0.05)."""
    return any(close(value, a) or close(value, a * 100) or close(value, a / 100) for a in allowed)


def _shown_texts(scene: dict) -> list[tuple[str, str]]:
    params = scene.get("visual", {}).get("params", {})
    return ([("label", t) for t in params.get("labels", [])] + [("step", t) for t in params.get("steps", [])])


def audit_numbers(data: dict, policy: NumericPolicy, allowed: set[float] | None = None) -> list[str]:
    """Every numeric violation in narration, labels and steps, as retry-ready messages. Empty list = clean."""
    allowed = allowed or set()
    problems = []
    for scene in data.get("scenes", []):
        sid = scene.get("id")
        texts = [("narration", scene.get("narration", ""))] + _shown_texts(scene)
        for field, raw in texts:
            text = nfkc(raw)
            if field != "narration":
                text = LIST_PREFIX.sub("", text)
            values = [v for v, _, _ in digit_number_spans(text) + spoken_number_spans(text)]
            if policy == "none":
                bad = [v for v in values if not is_small_int(v)]
                if bad:
                    problems.append(f"Scene {sid} {field} {raw!r} has quantities {_show(bad)}; this is a descriptive "
                                    "topic, so use qualitative words (heavy rain, several months, much larger).")
                if (unit := UNIT_WORDS.search(text)):
                    problems.append(f"Scene {sid} {field} {raw!r} uses the unit {unit.group(0)!r}; descriptive topics "
                                    "use no measurements, only qualitative words.")
                if "=" in text:
                    problems.append(f"Scene {sid} {field} {raw!r} contains '='; descriptive topics have no formulas.")
            else:
                bad = [v for v in values if not is_small_int(v) and not in_allowed(v, allowed)]
                if bad:
                    problems.append(f"Scene {sid} {field} {raw!r} has numbers {_show(bad)} that are not part of the "
                                    "checked worked example; every number must come from check.expr or its result.")
    return problems


def _show(values: list[float]) -> str:
    return ", ".join(str(int(v)) if v == int(v) else str(v) for v in values)
