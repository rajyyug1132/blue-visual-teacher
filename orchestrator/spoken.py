# orchestrator/spoken.py — turn digits and symbols into words so narration passes the spoken-only rule.
import re
import unicodedata

ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
        "seventeen eighteen nineteen").split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
SCALES = [(10**9, "billion"), (10**6, "million"), (1000, "thousand"), (100, "hundred")]
ORDINAL_FIX = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth",
               "nine": "ninth", "twelve": "twelfth"}
SYMBOLS = [("=", " equals "), ("×", " times "), ("÷", " divided by "), ("+", " plus "), ("<", " less than "),
           (">", " greater than "), ("%", " percent "), ("Ω", " ohms "), ("^", " to the power of "),
           ("°C", " degrees Celsius "), ("°F", " degrees Fahrenheit "), ("°", " degrees "), ("√", " square root of "),
           ("π", " pi "), ("/", " over "), ("\\", " ")]
# Common chemistry and unit tokens read as words rather than letter-by-letter ("CO2" -> "carbon dioxide").
# Matched after NFKC, so CO₂ and km² are covered too. Also a safety net for text going to TTS: speak_forms().
SPEAK_FORMS = [(r"\bC6H12O6\b", "glucose"), (r"\b6\s?CO2\b", "six carbon dioxide"), (r"\bCO2\b", "carbon dioxide"),
               (r"\b6\s?H2O\b", "six water"), (r"\bH2O\b", "water"), (r"\b6\s?O2\b", "six oxygen"),
               (r"\bO2\b", "oxygen"), (r"\bCH4\b", "methane"), (r"\bNaCl\b", "salt"), (r"\bH2\b", "hydrogen"),
               (r"\bN2\b", "nitrogen"), (r"(?<=\d)\s?km2\b", " square kilometres"), (r"\bkm2\b", "square kilometres"),
               (r"(?<=\d)\s?m2\b", " square metres"), (r"(?<=\d)\s?cm2\b", " square centimetres"),
               (r"(?<=\d)\s?m3\b", " cubic metres")]


def speak_forms(text: str) -> str:
    """NFKC, then common formulas/units as words. Safe to run on any text headed for TTS."""
    t = unicodedata.normalize("NFKC", text)
    for pattern, words in SPEAK_FORMS:
        t = re.sub(pattern, words, t)
    return t


def int_to_words(n: int) -> str:
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else "-" + ONES[n % 10])
    for value, name in SCALES:
        if n >= value:
            head, rest = divmod(n, value)
            return f"{int_to_words(head)} {name}" + ("" if rest == 0 else " " + int_to_words(rest))
    raise ValueError(n)


def _decade(match: re.Match) -> str:
    n = int(match.group(1))
    if n % 100 == 0:
        return f"{int_to_words(n // 100)} hundreds" if n < 2000 else "two thousands"
    words = f"{int_to_words(n // 100)} {int_to_words(n % 100)}"
    return words[:-1] + "ies" if words.endswith("y") else words + "s"


def _number(match: re.Match) -> str:
    raw = match.group(0)
    whole, _, frac = raw.replace(",", "").partition(".")
    n = int(whole)
    if not frac and "," not in raw and len(whole) == 4 and 1100 <= n <= 2099 and n % 100 != 0:
        # Read like a year: 1947 -> nineteen forty-seven, 2005 -> two thousand five
        if 2000 <= n <= 2009:
            return int_to_words(n)
        return f"{int_to_words(n // 100)} {int_to_words(n % 100) if n % 100 >= 10 else 'oh ' + ONES[n % 100]}"
    words = int_to_words(n)
    if frac:
        words += " point " + " ".join(ONES[int(d)] for d in frac)
    return words


def _ordinal(match: re.Match) -> str:
    words = int_to_words(int(match.group(1)))
    head, _, last = words.rpartition(" ")
    stem, dash, unit = last.rpartition("-")
    if unit in ORDINAL_FIX:
        unit = ORDINAL_FIX[unit]
    elif unit.endswith("y"):
        unit = unit[:-1] + "ieth"
    else:
        unit += "th"
    return (head + " " if head else "") + stem + dash + unit


def to_spoken(text: str) -> str:
    """Spell out numbers and symbols: "230 V across 46 Ω gives 5 A" -> "two hundred thirty V across ..."."""
    t = speak_forms(text)
    t = re.sub(r"(?:Rs\.?|₹)\s?(\d[\d,]*(?:\.\d+)?)", r"\1 rupees", t)
    t = re.sub(r"\$\s?(\d[\d,]*(?:\.\d+)?)", r"\1 dollars", t)
    t = re.sub(r"\b(\d+)(?:st|nd|rd|th)\b", _ordinal, t)
    t = re.sub(r"\b(1\d\d0|20\d0)'?s\b", _decade, t)  # 1960s -> nineteen sixties
    t = re.sub(r"(?<=\d)-(?=[A-Za-z])", " ", t)  # 230-Volt -> 230 Volt
    t = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", t)  # CO2 -> CO 2, 6CO2 -> 6 CO 2
    t = re.sub(r"\d+(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?", _number, t)  # 12,762.82 and Indian 1,00,000
    for sym, word in SYMBOLS:
        t = t.replace(sym, word)
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    return " ".join(t.split())


CLAUSE_BREAK = re.compile(r",\s+(?:where|which|while|so|and|but)\b|;\s+")


def shorten_narration(text: str, max_words: int | None = None, min_words: int | None = None) -> str | None:
    """Trim an overlong narration to complete sentences, or to a clause break; None if that is impossible."""
    from orchestrator.schema import WORDS_MAX, WORDS_MIN

    max_words = 32 if max_words is None else max_words
    min_words = 14 if min_words is None else min_words
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = []
    for sentence in sentences:
        if len(" ".join(kept + [sentence]).split()) > max_words:
            break
        kept.append(sentence)
    if kept and len(" ".join(kept).split()) >= min_words:
        return " ".join(kept)
    # Whole sentences don't fit (one long sentence, often cut off by the grammar's maxLength, or a short sentence
    # followed by a long one): keep the longest prefix that ends at a clause break and fits.
    full = text.strip()
    heads = [full[:m.start()] for m in CLAUSE_BREAK.finditer(full)]
    heads = [h for h in heads if min_words <= len(h.split()) <= max_words]
    return heads[-1].rstrip(" ,;:") + "." if heads else None
