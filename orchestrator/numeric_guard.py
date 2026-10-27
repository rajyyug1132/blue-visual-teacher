# orchestrator/numeric_guard.py — which numbers a lesson may contain, read from narration, labels and steps.
#
# NumericPolicy (decided once per topic by a tiny classify call in planner.py):
#   none    descriptive topic (Monsoon, Mughal Empire): no quantities at all. No digits, no number words above ten,
#           no units of measurement and no "=" in narration, labels or steps. Years 1000-2100 are dates, so allowed.
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


SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
YEAR_MIN, YEAR_MAX = 1000, 2100
DECADES = {w: 10 * (i + 2) for i, w in enumerate("twenties thirties forties fifties sixties seventies eighties nineties"
                                                 .split())}


def nfkc(text: str) -> str:
    """CO₂ -> CO2 for the digit rules, but a power stays a power: 6² -> 6^2 (plain NFKC would make it "62")."""
    text = re.sub(r"(?<=[\w)])([⁰¹²³⁴⁵⁶⁷⁸⁹]+)", lambda m: "^" + m.group(1).translate(SUPERSCRIPT), text)
    return unicodedata.normalize("NFKC", text)


def year_spans(text: str) -> list[tuple[float, int, int]]:
    """Years a history/civics lesson may state: 4-digit 1000-2100 ("1947", "1526-1858") or spoken in year form
    ("nineteen forty-seven", "twenty twenty-four", "the nineteen sixties"). "One thousand nine hundred" is not."""
    spans = [(float(m.group(0)), m.start(), m.end()) for m in re.finditer(r"(?<![\d,.])\d{4}(?![\d,.]\d)", text)
             if YEAR_MIN <= int(m.group(0)) <= YEAR_MAX]
    # Era-marked dates of any length: "321-185 BCE", "563 BC", "AD 1206", "78 CE" (ancient history needs them).
    for m in re.finditer(r"(?<![\d,.])(\d{1,4})(?:\s*[-–]\s*(\d{1,4}))?\s*(?:BCE|BC|CE|AD)\b|\bAD\s*(\d{1,4})\b", text):
        for g in (1, 2, 3):
            if m.group(g):
                spans.append((float(m.group(g)), m.start(g), m.end(g)))
    spans += [(v, s, e) for v, s, e in spoken_number_spans(text)
              if YEAR_MIN <= v <= YEAR_MAX and v == int(v) and not re.search(r"hundred|thousand", text[s:e], re.I)]
    return spans


def spoken_number_spans(text: str) -> list[tuple[float, int, int]]:
    """Numbers written as words, with their character spans: "fifty-five degrees" -> [(55, 0, 10)].

    Year-aware: a teen or "twenty" followed by a tens word, a teen, "oh" or a decade reads as a year
    ("nineteen sixty" = 1960, not 79). Punctuation ends a number, so "ten, thirty, fifty" is three numbers.
    """
    toks = [(m.group(0), m.start(), m.end()) for m in re.finditer(r"[a-z]+", text.lower())]
    out = []
    total = cur = 0
    start = end = None
    active = False
    head = False  # cur so far is a single teen / "twenty" word: a year may follow

    def flush():
        nonlocal total, cur, active, start, end, head
        if active:
            out.append((float(total + cur), start, end))
        total = cur = 0
        active = head = False
        start = end = None

    i = 0
    while i < len(toks):
        w, s, e = toks[i]
        if active and text[end:s].strip(" -") not in ("", "and"):
            flush()  # a comma, full stop or other word-break between two number words
        year_next = w in TENS or w in DECADES or w == "oh" or (w in UNITS and UNITS[w] >= 10)
        if head and total == 0 and year_next:
            cur = cur * 100 + (0 if w == "oh" else UNITS.get(w, TENS.get(w, DECADES.get(w, 0))))
            head, end = False, e
        elif w in UNITS or w in TENS:
            if not active:
                start = s
            head = not active and (11 <= UNITS.get(w, 0) <= 19 or w == "twenty")
            cur += UNITS.get(w, TENS.get(w))
            active, end = True, e
        elif w == "hundred" and active:
            cur, end, head = (cur or 1) * 100, e, False
        elif w in BIG and active:
            total, cur, end, head = total + (cur or 1) * BIG[w], 0, e, False
        elif w == "point" and active:
            j, frac = i + 1, ""
            while j < len(toks) and toks[j][0] in UNITS and UNITS[toks[j][0]] < 10:
                frac += str(UNITS[toks[j][0]])
                end = toks[j][2]
                j += 1
            if frac:
                out.append((total + cur + float("0." + frac), start, end))
                total = cur = 0
                active = head = False
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
    return [issue["message"] for issue in audit_fields(data, policy, allowed)]


def audit_fields(data: dict, policy: NumericPolicy, allowed: set[float] | None = None) -> list[dict]:
    """Violations with their location, so the planner can patch just that string:
    {scene_index, field: narration|label|step, idx (list index, None for narration), text, kind, message}.
    kind is numbers, unit or equals."""
    allowed = allowed or set()
    problems = []
    for si, scene in enumerate(data.get("scenes", [])):
        sid = scene.get("id")
        params = scene.get("visual", {}).get("params", {})
        texts = ([("narration", None, scene.get("narration", ""))]
                 + [("label", i, t) for i, t in enumerate(params.get("labels", []))]
                 + [("step", i, t) for i, t in enumerate(params.get("steps", []))])

        def add(kind, message, field=None, idx=None, raw=None):
            problems.append({"scene_index": si, "field": field, "idx": idx, "text": raw, "kind": kind,
                             "message": message})

        for field, idx, raw in texts:
            if not isinstance(raw, str):
                continue
            text = nfkc(raw)
            if field != "narration":
                text = LIST_PREFIX.sub("", text)
            # Messages name the problem and the field only: sample replacement words get copied verbatim by
            # small models ("uses heavy rain of water"), so never suggest any.
            years = {(s, e) for _, s, e in year_spans(text)}  # dates are facts, not quantities
            values = [v for v, s, e in digit_number_spans(text) + spoken_number_spans(text) if (s, e) not in years]
            where = f"scene {sid} {field}"
            if policy == "none":
                bad = [v for v in values if not is_small_int(v)]
                if bad:
                    add("numbers", f"Remove the numbers ({_show(bad)}) from {where}, keep the sentence natural. "
                                   "This topic is descriptive.", field, idx, raw)
                if (unit := UNIT_WORDS.search(text)):
                    add("unit", f"Remove the unit {unit.group(0)!r} from {where}, keep the sentence natural.",
                        field, idx, raw)
                if "=" in text:
                    add("equals", f"Remove '=' from {where}, keep the text natural. This topic has no formula.",
                        field, idx, raw)
            else:
                bad = [v for v in values if not is_small_int(v) and not in_allowed(v, allowed)]
                if bad:
                    add("numbers", f"Remove the numbers ({_show(bad)}) from {where}, keep the sentence natural. "
                                   "Only numbers from the checked worked example may appear.", field, idx, raw)
    return problems


def _show(values: list[float]) -> str:
    return ", ".join(str(int(v)) if v == int(v) else str(v) for v in values)
