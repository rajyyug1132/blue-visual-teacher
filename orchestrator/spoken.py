# orchestrator/spoken.py — turn digits and symbols into words so narration passes the spoken-only rule.
import re

ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
        "seventeen eighteen nineteen").split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
SCALES = [(10**9, "billion"), (10**6, "million"), (1000, "thousand"), (100, "hundred")]
ORDINAL_FIX = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth",
               "nine": "ninth", "twelve": "twelfth"}
SYMBOLS = [("=", " equals "), ("×", " times "), ("÷", " divided by "), ("+", " plus "), ("<", " less than "),
           (">", " greater than "), ("%", " percent "), ("Ω", " ohms "), ("^", " to the power of "),
           ("/", " over "), ("\\", " ")]


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
    t = re.sub(r"(?:Rs\.?|₹)\s?(\d[\d,]*(?:\.\d+)?)", r"\1 rupees", text)
    t = re.sub(r"\$\s?(\d[\d,]*(?:\.\d+)?)", r"\1 dollars", t)
    t = re.sub(r"\b(\d+)(?:st|nd|rd|th)\b", _ordinal, t)
    t = re.sub(r"(?<=\d)-(?=[A-Za-z])", " ", t)  # 230-Volt -> 230 Volt
    t = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", t)  # CO2 -> CO 2, 6CO2 -> 6 CO 2
    t = re.sub(r"\d+(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?", _number, t)  # 12,762.82 and Indian 1,00,000
    for sym, word in SYMBOLS:
        t = t.replace(sym, word)
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    return " ".join(t.split())
