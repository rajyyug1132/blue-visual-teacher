"""localization/normalize.py — Spoken normalization, residual digit expansion, and MMS-TTS text cleaning.

Pipeline stages:
  1. speak_en(text): Pre-translation normalization of English narration.
     Expands mathematical symbols (=, +, ×, ÷), temperatures (100 °C), percentages (6.5%),
     and scientific units (230 V, 46 Ω) into natural spoken English before IndicTrans2.
  2. fix_residual_digits(text, lang): Post-translation normalization.
     Converts any residual ASCII digits (0-9) or decimals into native script words in Hindi or Kannada.
  3. clean_for_mms(text, lang): Pre-TTS text sanitation for Meta MMS-TTS.
     Ensures 0 ASCII digits remain, expands/strips non-vocabulary symbols, and normalizes punctuation
     into natural speech pauses.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Number to Words (Kannada, Hindi, English)
# ---------------------------------------------------------------------------
def kannada_number_to_words(n: int) -> str:
    """Convert an integer (0 to 9999999) to Kannada words."""
    if n == 0:
        return "ಸೊನ್ನೆ"
    if n < 0:
        return "ಮೈನಸ್ " + kannada_number_to_words(abs(n))

    units = ["", "ಒಂದು", "ಎರಡು", "ಮೂರು", "ನಾಲ್ಕು", "ಐದು", "ಆರು", "ಏಳು", "ಎಂಟು", "ಒಂಬತ್ತು"]
    teens = [
        "ಹತ್ತು", "ಹನ್ನೊಂದು", "ಹನ್ನೆರಡು", "ಹದಿಮೂರು", "ಹದಿನಾಲ್ಕು",
        "ಹದಿನೈದು", "ಹದಿನಾರು", "ಹದಿನೇಳು", "ಹದಿನೆಂಟು", "ಹತ್ತೊಂಬತ್ತು"
    ]
    tens_exact = ["", "", "ಇಪ್ಪತ್ತು", "ಮೂವತ್ತು", "ನಲವತ್ತು", "ಐವತ್ತು", "ಅರವತ್ತು", "ಎಪ್ಪತ್ತು", "ಎಂಬತ್ತು", "ತೊಂಬತ್ತು"]
    tens_comb_sandhi = {
        2: "ಇಪ್ಪ", 3: "ಮೂವ", 4: "ನಲವ", 5: "ಐವ", 6: "ಅರವ", 7: "ಎಪ್ಪ", 8: "ಎಂಬ", 9: "ತೊಂಬ"
    }
    unit_sandhi = {
        1: "ತ್ತೊಂದು", 2: "ತ್ತೆರಡು", 3: "ತ್ತಮೂರು", 4: "ತ್ತನಾಲ್ಕು",
        5: "ತ್ತೈದು", 6: "ತ್ತಾರು", 7: "ತ್ತೇಳು", 8: "ತ್ತೆಂಟು", 9: "ತ್ತೊಂಬತ್ತು"
    }
    hundreds_exact = [
        "", "ನೂರು", "ಇನ್ನೂರು", "ಮುನ್ನೂರು", "ನಾನೂರು",
        "ಐನೂರು", "ಆರುನೂರು", "ಏಳುನೂರು", "ಎಂಟುನೂರು", "ಒಂಬೈನೂರು"
    ]
    hundreds_comb = [
        "", "ನೂರ ", "ಇನ್ನೂರ ", "ಮುನ್ನೂರ ", "ನಾನೂರಾ ",
        "ಐನೂರ ", "ಆರುನೂರ ", "ಏಳುನೂರ ", "ಎಂಟುನೂರ ", "ಒಂಬೈನೂರ "
    ]

    if n < 10:
        return units[n]
    if n < 20:
        return teens[n - 10]
    if n < 100:
        ten, rem = n // 10, n % 10
        if rem == 0:
            return tens_exact[ten]
        return tens_comb_sandhi[ten] + unit_sandhi[rem]
    if n < 1000:
        h, rem = n // 100, n % 100
        if rem == 0:
            return hundreds_exact[h]
        return hundreds_comb[h] + kannada_number_to_words(rem)
    if n < 100000:
        th, rem = n // 1000, n % 1000
        th_word = kannada_number_to_words(th)
        if rem == 0:
            return th_word + " ಸಾವಿರ"
        return th_word + " ಸಾವಿರದ " + kannada_number_to_words(rem)
    if n < 10000000:
        lakh, rem = n // 100000, n % 100000
        lakh_word = kannada_number_to_words(lakh)
        if rem == 0:
            return lakh_word + " ಲಕ್ಷ"
        return lakh_word + " ಲಕ್ಷದ " + kannada_number_to_words(rem)

    return str(n)


def hindi_number_to_words(n: int) -> str:
    """Convert an integer (0 to 9999999) to Hindi words."""
    if n == 0:
        return "शून्य"
    if n < 0:
        return "माइनस " + hindi_number_to_words(abs(n))

    words_0_to_99 = {
        1: "एक", 2: "दो", 3: "तीन", 4: "चार", 5: "पाँच", 6: "छह", 7: "सात", 8: "आठ", 9: "नौ", 10: "दस",
        11: "ग्यारह", 12: "बारह", 13: "तेरह", 14: "चौदह", 15: "पंद्रह", 16: "सोलह", 17: "सत्रह", 18: "अठारह", 19: "उन्नीस", 20: "बीस",
        21: "इक्कीस", 22: "बाईस", 23: "तेईस", 24: "चौबीस", 25: "पच्चीस", 26: "छब्बीस", 27: "सत्ताईस", 28: "अट्ठाईस", 29: "उनतीस", 30: "तीस",
        31: "इकत्तीस", 32: "बत्तीस", 33: "तैंतीस", 34: "चौंतीस", 35: "पैंतीस", 36: "छत्तीस", 37: "सैंतीस", 38: "अड़तीस", 39: "उनतालीस", 40: "चालीस",
        41: "इकतालीस", 42: "बयालीस", 43: "तैंतालीस", 44: "चौवालीस", 45: "पैंतालीस", 46: "छियालीस", 47: "सैंतालीस", 48: "अड़तालीस", 49: "उनचास", 50: "पचास",
        51: "इक्यावन", 52: "बावन", 53: "तिरपन", 54: "चौवन", 55: "पचपन", 56: "छप्पन", 57: "सत्तावन", 58: "अट्ठावन", 59: "उनसठ", 60: "साठ",
        61: "इकसठ", 62: "बासठ", 63: "तिरसठ", 64: "चौंसठ", 65: "पैंसठ", 66: "छियासठ", 67: "सरसठ", 68: "अड़सठ", 69: "उनहत्तर", 70: "सत्तर",
        71: "इकहत्तर", 72: "बहत्तर", 73: "तिहत्तर", 74: "चौहत्तर", 75: "पचहत्तर", 76: "छिहत्तर", 77: "सतहत्तर", 78: "अठहत्तर", 79: "उन्नासी", 80: "अस्सी",
        81: "इक्यासी", 82: "बयासी", 83: "तिरासी", 84: "चौरासी", 85: "पचासी", 86: "छियासी", 87: "सत्तासी", 88: "अट्ठासी", 89: "नवासी", 90: "नब्बे",
        91: "इक्यानवे", 92: "बानवे", 93: "तिरानवे", 94: "चौरानवे", 95: "पंचानवे", 96: "छियानवे", 97: "सत्तानवे", 98: "अट्ठानवे", 99: "निन्यानवे"
    }

    if n < 100:
        return words_0_to_99[n]
    if n < 1000:
        h, rem = n // 100, n % 100
        prefix = f"{words_0_to_99[h]} सौ"
        return f"{prefix} {hindi_number_to_words(rem)}" if rem else prefix
    if n < 100000:
        th, rem = n // 1000, n % 1000
        prefix = f"{hindi_number_to_words(th)} हज़ार"
        return f"{prefix} {hindi_number_to_words(rem)}" if rem else prefix
    if n < 10000000:
        lakh, rem = n // 100000, n % 100000
        prefix = f"{hindi_number_to_words(lakh)} लाख"
        return f"{prefix} {hindi_number_to_words(rem)}" if rem else prefix

    return str(n)


def english_number_to_words(n: int) -> str:
    """Convert an integer (0 to 9999999) to English words."""
    if n == 0:
        return "zero"
    if n < 0:
        return "minus " + english_number_to_words(abs(n))

    units = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    teens = [
        "ten", "eleven", "twelve", "thirteen", "fourteen",
        "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"
    ]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

    if n < 10:
        return units[n]
    if n < 20:
        return teens[n - 10]
    if n < 100:
        ten, rem = n // 10, n % 10
        return f"{tens[ten]}-{units[rem]}" if rem else tens[ten]
    if n < 1000:
        h, rem = n // 100, n % 100
        prefix = f"{units[h]} hundred"
        return f"{prefix} {english_number_to_words(rem)}" if rem else prefix
    if n < 1000000:
        th, rem = n // 1000, n % 1000
        prefix = f"{english_number_to_words(th)} thousand"
        return f"{prefix} {english_number_to_words(rem)}" if rem else prefix

    return str(n)


# ---------------------------------------------------------------------------
def tamil_number_to_words(n: int) -> str:
    """Convert an integer (0 to 9999999) to Tamil words."""
    if n == 0:
        return "பூஜ்ஜியம்"
    if n < 0:
        return "மைனஸ் " + tamil_number_to_words(abs(n))

    units = ["", "ஒன்று", "இரண்டு", "மூன்று", "நான்கு", "ஐந்து", "ஆறு", "ஏழு", "எட்டு", "ஒன்பது"]
    teens = [
        "பத்து", "பதினொன்று", "பன்னிரண்டு", "பதின்மூன்று", "பதினான்கு",
        "பதினைந்து", "பதினாறு", "பதினேழு", "பதினெட்டு", "பத்தொன்பது"
    ]
    tens_exact = ["", "", "இருபது", "முப்பது", "நாற்பது", "ஐம்பது", "அறுபது", "எழுபது", "எண்பது", "தொண்ணூறு"]
    tens_comb = ["", "", "இருபத்து ", "முப்பத்து ", "நாற்பத்து ", "ஐம்பத்து ", "அறுபத்து ", "எழுபத்து ", "எண்பத்து ", "தொண்ணூற்று "]
    hundreds_exact = ["", "நூறு", "இருநூறு", "முந்நூறு", "நானூறு", "ஐந்நூறு", "அறுநூறு", "எழுநூறு", "எண்ணூறு", "தொள்ளாயிரம்"]
    hundreds_comb = ["", "நூற்று ", "இருநூற்று ", "முந்நூற்று ", "நானூற்று ", "ஐந்நூற்று ", "அறுநூற்று ", "எழுநூற்று ", "எண்ணூற்று ", "தொள்ளாயிரத்து "]

    if n < 10:
        return units[n]
    if n < 20:
        return teens[n - 10]
    if n < 100:
        ten, rem = n // 10, n % 10
        return tens_exact[ten] if rem == 0 else (tens_comb[ten] + units[rem])
    if n < 1000:
        h, rem = n // 100, n % 100
        return hundreds_exact[h] if rem == 0 else (hundreds_comb[h] + tamil_number_to_words(rem))
    if n < 100000:
        th, rem = n // 1000, n % 1000
        if th == 1:
            prefix = "ஆயிரத்து " if rem else "ஆயிரம்"
        else:
            th_w = tamil_number_to_words(th)
            prefix = f"{th_w} ஆயிரத்து " if rem else f"{th_w} ஆயிரம்"
        return prefix if rem == 0 else (prefix + tamil_number_to_words(rem))
    if n < 10000000:
        lakh, rem = n // 100000, n % 100000
        lakh_w = tamil_number_to_words(lakh)
        prefix = f"{lakh_w} இலட்சத்து " if rem else f"{lakh_w} இலட்சம்"
        return prefix if rem == 0 else (prefix + tamil_number_to_words(rem))

    return str(n)



# ---------------------------------------------------------------------------
bengali_digits_0_to_99 = {
    0: "শূন্য", 1: "এক", 2: "দুই", 3: "তিন", 4: "চার", 5: "পাঁচ", 6: "ছয়", 7: "সাত", 8: "আট", 9: "নয়", 10: "দশ",
    11: "এগারো", 12: "বারো", 13: "তেরো", 14: "চৌদ্দ", 15: "পনেরো", 16: "ষোলো", 17: "সতেরো", 18: "আঠারো", 19: "উনিশ", 20: "বিশ",
    21: "একুশ", 22: "বাইশ", 23: "তেইশ", 24: "চব্বিশ", 25: "পঁচিশ", 26: "ছাব্বিশ", 27: "সাতাশ", 28: "আঠাশ", 29: "ঊনত্রিশ", 30: "ত্রিশ",
    31: "একত্রিশ", 32: "বত্রিশ", 33: "তেত্রিশ", 34: "চৌত্রিশ", 35: "পঁয়ত্রিশ", 36: "ছত্রিশ", 37: "সাঁইত্রিশ", 38: "আটত্রিশ", 39: "ঊনচল্লিশ", 40: "চল্লিশ",
    41: "একচল্লিশ", 42: "বিয়াল্লিশ", 43: "তেতাল্লিশ", 44: "চুয়াল্লিশ", 45: "পঁয়তাল্লিশ", 46: "ছেচল্লিশ", 47: "সাতচল্লিশ", 48: "আটচল্লিশ", 49: "ঊনপঞ্চাশ", 50: "পঞ্চাশ",
    51: "একান্ন", 52: "বায়ান্ন", 53: "তিপ্পান্ন", 54: "চুয়ান্ন", 55: "পঞ্চান্ন", 56: "ছাপ্পান্ন", 57: "সাতান্ন", 58: "আটান্ন", 59: "ঊনষাট", 60: "ষাট",
    61: "একষট্টি", 62: "বাষট্টি", 63: "তেষট্টি", 64: "চৌষট্টি", 65: "পঁয়ষট্টি", 66: "ছেষট্টি", 67: "সাতষট্টি", 68: "আটষট্টি", 69: "ঊনসত্তর", 70: "সত্তর",
    71: "একাত্তর", 72: "বাহাত্তর", 73: "তিয়াত্তর", 74: "চুয়াত্তর", 75: "পঁচাত্তর", 76: "ছিয়াত্তর", 77: "সাতাত্তর", 78: "আঠাত্তর", 79: "ঊনআশি", 80: "আশি",
    81: "একাশি", 82: "বিরাশি", 83: "তিরাশি", 84: "চৌরাশি", 85: "পঁচাশি", 86: "ছিয়াশি", 87: "সাতাশি", 88: "অষ্টআশি", 89: "ঊননব্বই", 90: "নব্বই",
    91: "একানব্বই", 92: "বিরানব্বই", 93: "তিরানব্বই", 94: "চৌরানব্বই", 95: "পঁচানব্বই", 96: "ছিয়ানব্বই", 97: "সাতানব্বই", 98: "আটানব্বই", 99: "নিরানব্বই"
}

def bengali_number_to_words(n: int) -> str:
    """Convert an integer (0 to 9999999) to Bengali words."""
    if n == 0:
        return "শূন্য"
    if n < 0:
        return "মাইনাস " + bengali_number_to_words(abs(n))
    if n < 100:
        return bengali_digits_0_to_99[n]
    if n < 1000:
        h, rem = n // 100, n % 100
        prefix = "একশো" if h == 1 else f"{bengali_digits_0_to_99[h]}শো"
        return f"{prefix} {bengali_number_to_words(rem)}" if rem else prefix
    if n < 100000:
        th, rem = n // 1000, n % 1000
        prefix = "এক হাজার" if th == 1 else f"{bengali_number_to_words(th)} হাজার"
        return f"{prefix} {bengali_number_to_words(rem)}" if rem else prefix
    if n < 10000000:
        lakh, rem = n // 100000, n % 100000
        prefix = "এক লাখ" if lakh == 1 else f"{bengali_number_to_words(lakh)} লাখ"
        return f"{prefix} {bengali_number_to_words(rem)}" if rem else prefix
    return str(n)


# ---------------------------------------------------------------------------
# 1. speak_en(text) — Pre-translation English normalization
# ---------------------------------------------------------------------------
def speak_en(text: str) -> str:
    """Normalize English narration into spoken English before sending to IndicTrans2.
    
    Expands:
      - Temperatures: "100 °C" -> "100 degrees Celsius"
      - Percentages: "6.5%" -> "6.5 percent"
      - Electrical & physics units: "230 V" -> "230 volts", "46 Ω" -> "46 ohms"
      - Math operators: "H = 2" -> "H equals 2", "V = I × R" -> "V equals I times R"
    """
    out = text

    # Temperature: 100 °C, 100°C, 37 deg C
    out = re.sub(r"(\d+(?:\.\d+)?)\s*(?:°\s*C|deg\s*C|degrees\s*C)\b", r"\1 degrees Celsius", out, flags=re.IGNORECASE)
    out = re.sub(r"(\d+(?:\.\d+)?)\s*(?:°\s*F|deg\s*F)\b", r"\1 degrees Fahrenheit", out, flags=re.IGNORECASE)

    # Percentage: 6.5%, 100%
    out = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"\1 percent", out)

    # Electrical & physical units
    unit_map = [
        (r"\b(\d+(?:\.\d+)?)\s*(?:Ω|Ohms?)\b", r"\1 ohms"),
        (r"\b(\d+(?:\.\d+)?)\s*(?:V|Volts?)\b", r"\1 volts"),
        (r"\b(\d+(?:\.\d+)?)\s*(?:A|Amperes?|Amps?)\b", r"\1 amperes"),
        (r"\b(\d+(?:\.\d+)?)\s*(?:W|Watts?)\b", r"\1 watts"),
        (r"\b(\d+(?:\.\d+)?)\s*(?:Hz|Hertz)\b", r"\1 hertz"),
        (r"\b(\d+(?:\.\d+)?)\s*(?:kHz)\b", r"\1 kilohertz"),
        (r"\b(\d+(?:\.\d+)?)\s*(?:fps)\b", r"\1 frames per second"),
        (r"\b(\d+(?:\.\d+)?)\s*(?:m\/s\^2|m\/s2)\b", r"\1 meters per second squared"),
        (r"\b(\d+(?:\.\d+)?)\s*(?:m\/s)\b", r"\1 meters per second"),
        (r"\b(\d+(?:\.\d+)?)\s*(?:sec|s)\b", r"\1 seconds"),
    ]
    for pat, repl in unit_map:
        out = re.sub(pat, repl, out)

    # Math operators & symbols when used in formulas or equations
    out = re.sub(r"\s*=\s*", " equals ", out)
    out = re.sub(r"\s*(?:×|\*)\s*", " times ", out)
    out = re.sub(r"\s*(?:÷|\/)\s*", " divided by ", out)
    out = re.sub(r"\s*\+\s*", " plus ", out)
    out = re.sub(r"(?<=\w)\s*-\s*(?=\w)", " minus ", out)
    out = re.sub(r"\s*→\s*", " leads to ", out)

    # Collapse extra whitespace
    return re.sub(r"\s+", " ", out).strip()


# ---------------------------------------------------------------------------
# 2. fix_residual_digits(text, lang) — Post-translation digit expansion
# ---------------------------------------------------------------------------
def fix_residual_digits(text: str, lang: str) -> str:
    """Convert any residual ASCII digits into native script words in Hindi or Kannada.
    
    Converts:
      - Decimals: "6.5" -> "छह दशमलव पाँच" (hi), "ಆರು ಬಿಂದು ಐದು" (kn)
      - Integers: "230" -> "दो सौ तीस" (hi), "ಇನ್ನೂರ ಮೂವತ್ತು" (kn)
      - Years: "2023" -> "दो हज़ार तेईस" (hi), "ಎರಡು ಸಾವಿರದ ಇಪ್ಪತ್ತಮೂರು" (kn)
    """
    out = text

    # Decimals: 6.5 -> 'ಆರು ಬಿಂದು ಐದು' / 'छह दशमलव पाँच'
    def _replace_decimal(m: re.Match) -> str:
        int_part = int(m.group(1))
        dec_digits = m.group(2)
        if lang in ("kn", "kan_Knda"):
            int_w = kannada_number_to_words(int_part)
            dec_w = " ".join(kannada_number_to_words(int(d)) for d in dec_digits)
            return f"{int_w} ಬಿಂದು {dec_w}"
        elif lang in ("hi", "hin_Deva"):
            int_w = hindi_number_to_words(int_part)
            dec_w = " ".join(hindi_number_to_words(int(d)) for d in dec_digits)
            return f"{int_w} दशमलव {dec_w}"
        elif lang in ("ta", "tam_Taml"):
            int_w = tamil_number_to_words(int_part)
            dec_w = " ".join(tamil_number_to_words(int(d)) for d in dec_digits)
            return f"{int_w} புள்ளி {dec_w}"
        elif lang in ("bn", "ben_Beng"):
            int_w = bengali_number_to_words(int_part)
            dec_w = " ".join(bengali_number_to_words(int(d)) for d in dec_digits)
            return f"{int_w} দশমিক {dec_w}"
        else:
            int_w = english_number_to_words(int_part)
            dec_w = " ".join(english_number_to_words(int(d)) for d in dec_digits)
            return f"{int_w} point {dec_w}"

    out = re.sub(r"\b(\d+)\.(\d+)\b", _replace_decimal, out)

    # Standalone unit/math symbols that might remain
    if lang in ("kn", "kan_Knda"):
        out = re.sub(r"(\b\d+\b)\s*%", r"\1 ಪ್ರತಿಶತ", out)
        out = re.sub(r"°\s*C", "ಡಿಗ್ರಿ ಸೆಲ್ಸಿಯಸ್", out)
        out = re.sub(r"°\s*F", "ಡಿಗ್ರಿ ಫ್ಯಾರನ್‌ಹೀಟ್", out)
        out = re.sub(r"Ω", "ಓಮ್", out)
        out = re.sub(r"\s*=\s*", " ಸಮಾನ ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " ಗುಣಿಸು ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " ಭಾಗಿಸು ", out)
        out = re.sub(r"\s*\+\s*", " ಪ್ಲಸ್ ", out)
        out = re.sub(r"\s*-\s*", " ಮೈನಸ್ ", out)
        out = re.sub(r"\s*→\s*", " ಕಾರಣವಾಗುತ್ತದೆ ", out)

        def _replace_int_kn(m: re.Match) -> str:
            return kannada_number_to_words(int(m.group(0)))

        out = re.sub(r"\b\d+\b", _replace_int_kn, out)

    elif lang in ("hi", "hin_Deva"):
        out = re.sub(r"(\b\d+\b)\s*%", r"\1 प्रतिशत", out)
        out = re.sub(r"°\s*C", "डिग्री सेल्सियस", out)
        out = re.sub(r"°\s*F", "डिग्री फ़ारेनहाइट", out)
        out = re.sub(r"Ω", "ओम", out)
        out = re.sub(r"\s*=\s*", " बराबर ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " गुणा ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " भागाकार ", out)
        out = re.sub(r"\s*\+\s*", " प्लस ", out)
        out = re.sub(r"\s*-\s*", " माइनस ", out)
        out = re.sub(r"\s*→\s*", " की ओर ", out)

        def _replace_int_hi(m: re.Match) -> str:
            return hindi_number_to_words(int(m.group(0)))

        out = re.sub(r"\b\d+\b", _replace_int_hi, out)

    elif lang in ("ta", "tam_Taml"):
        out = re.sub(r"(\b\d+\b)\s*%", r"\1 சதவீதம்", out)
        out = re.sub(r"°\s*C", "டிகிரி செல்சியஸ்", out)
        out = re.sub(r"°\s*F", "டிகிரி பாரன்ஹீட்", out)
        out = re.sub(r"Ω", "ஓம்", out)
        out = re.sub(r"\s*=\s*", " சமம் ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " பெருக்கல் ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " வகுத்தல் ", out)
        out = re.sub(r"\s*\+\s*", " கூட்டல் ", out)
        out = re.sub(r"\s*-\s*", " கழித்தல் ", out)
        out = re.sub(r"\s*→\s*", " வழிவகுக்கிறது ", out)

        def _replace_int_ta(m: re.Match) -> str:
            return tamil_number_to_words(int(m.group(0)))

        out = re.sub(r"\b\d+\b", _replace_int_ta, out)

    elif lang in ("bn", "ben_Beng"):
        out = re.sub(r"(\b\d+\b)\s*%", r"\1 শতাংশ", out)
        out = re.sub(r"°\s*C", "ডিগ্রি সেলসিয়াস", out)
        out = re.sub(r"°\s*F", "ডিগ্রি ফারেনহাইট", out)
        out = re.sub(r"Ω", "ওহম", out)
        out = re.sub(r"\s*=\s*", " সমান ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " গুণ ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " ভাগ ", out)
        out = re.sub(r"\s*\+\s*", " প্লাস ", out)
        out = re.sub(r"\s*-\s*", " মাইনাস ", out)
        out = re.sub(r"\s*→\s*", " বোঝায় ", out)

        def _replace_int_bn(m: re.Match) -> str:
            return bengali_number_to_words(int(m.group(0)))

        out = re.sub(r"\b\d+\b", _replace_int_bn, out)

    else:
        out = re.sub(r"(\b\d+\b)\s*%", r"\1 percent", out)
        out = re.sub(r"°\s*C", "degrees Celsius", out)
        out = re.sub(r"°\s*F", "degrees Fahrenheit", out)
        out = re.sub(r"Ω", "ohms", out)
        out = re.sub(r"\s*=\s*", " equals ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " times ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " divided by ", out)
        out = re.sub(r"\s*\+\s*", " plus ", out)
        out = re.sub(r"\s*-\s*", " minus ", out)

        def _replace_int_en(m: re.Match) -> str:
            return english_number_to_words(int(m.group(0)))

        out = re.sub(r"\b\d+\b", _replace_int_en, out)

    return re.sub(r"\s+", " ", out).strip()


# ---------------------------------------------------------------------------
# STEM Acronyms & Context Disambiguation (2A: Collocation Window + 2B: Case)
# ---------------------------------------------------------------------------
STEM_DISAMBIGUATION: dict[str, dict] = {
    "RAM": {
        "stem_cues": {
            "memory", "ddr", "byte", "bytes", "kb", "mb", "gb", "tb", "processor",
            "cpu", "chip", "chips", "storage", "hardware", "device", "speed",
            "read", "write", "random", "access", "module", "motherboard", "computer",
            "laptop", "phone", "rom", "cache", "capacity", "ram", "ddr4", "ddr5"
        },
        "non_stem_cues": {
            "king", "lord", "shri", "raja", "ruled", "temple", "brother", "son",
            "prince", "chariot", "ayodhya", "sita", "laxman", "ramayana", "dynasty",
            "history", "story", "character", "saint", "person", "name", "god",
            "avatar", "animal", "sheep", "goat", "horn", "battering"
        },
        "default_caps_stem": True,
        "mapping": {"en": "RAM", "hi": "रैम", "kn": "ರ್ಯಾಮ್", "ta": "ரேம்", "bn": "র‌্যাম"},
    },
    "ROM": {
        "stem_cues": {
            "memory", "bios", "firmware", "chip", "chips", "storage", "boot",
            "hardware", "byte", "bytes", "mb", "gb", "cpu", "ram", "eeprom", "prom"
        },
        "non_stem_cues": {
            "rome", "ancient", "empire", "city", "gypsy", "people", "country", "italian"
        },
        "default_caps_stem": True,
        "mapping": {"en": "ROM", "hi": "रॉम", "kn": "ರಾಮ್", "ta": "ரோம்", "bn": "রম"},
    },
    "AC": {
        "stem_cues": {
            "current", "voltage", "circuit", "circuits", "dc", "supply", "mains",
            "frequency", "hz", "generator", "power", "alternating", "phase",
            "transformer", "electricity", "inverter", "dynamo", "motor", "grid"
        },
        "non_stem_cues": {
            "room", "cooling", "remote", "temperature", "conditioner", "filter",
            "car", "summer", "split", "duct", "window", "compressor", "cool",
            "degree", "celsius", "air"
        },
        "default_caps_stem": True,
        "mapping": {"en": "A C", "hi": "एसी", "kn": "ಎಸಿ", "ta": "ஏசி", "bn": "এসি"},
    },
    "DC": {
        "stem_cues": {
            "current", "voltage", "circuit", "circuits", "ac", "supply", "battery",
            "cell", "generator", "power", "direct", "polarity", "dynamo", "motor"
        },
        "non_stem_cues": {
            "commissioner", "district", "comics", "batman", "superman", "washington",
            "officer", "collector", "ias"
        },
        "default_caps_stem": True,
        "mapping": {"en": "D C", "hi": "डीसी", "kn": "ಡಿಸಿ", "ta": "டிசி", "bn": "ডিসি"},
    },
    "PI": {
        "stem_cues": {
            "circle", "radius", "diameter", "circumference", "area", "formula",
            "radians", "3.14", "22/7", "sphere", "cylinder", "perimeter", "angle",
            "trigonometry", "ratio", "constant"
        },
        "non_stem_cues": {
            "apple", "bake", "eat", "food", "dish", "recipe", "crust", "bakery",
            "detective", "investigator", "private"
        },
        "default_caps_stem": False,
        "allow_lowercase": True,
        "mapping": {"en": "pi", "hi": "पाई", "kn": "ಪೈ", "ta": "பை", "bn": "পাই"},
    },
    "LOG": {
        "stem_cues": {
            "base", "exponent", "math", "formula", "value", "table", "natural",
            "ln", "antilog", "scale", "decibel", "ph", "algorithm", "logarithm"
        },
        "non_stem_cues": {
            "wood", "tree", "fire", "timber", "forest", "cabin", "cut", "burning"
        },
        "default_caps_stem": False,
        "allow_lowercase": True,
        "mapping": {"en": "log", "hi": "लॉग", "kn": "ಲಾಗ್", "ta": "லாக்", "bn": "লগ"},
    },
    "ATM": {
        "stem_cues": {
            "pressure", "gas", "bar", "pascal", "mercury", "760", "sea", "level", "atmospheric"
        },
        "non_stem_cues": {
            "bank", "money", "cash", "withdraw", "card", "machine", "pin", "teller"
        },
        "default_caps_stem": False,
        "allow_lowercase": True,
        "mapping": {
            "en": "atmospheres",
            "hi": "वायुमंडल",
            "kn": "ವಾತಾವರಣ ಒತ್ತಡ",
            "ta": "வளிமண்டல அழுத்தம்",
            "bn": "বায়ুমণ্ডলীয় চাপ",
        },
    },
    "MOLE": {
        "stem_cues": {
            "chemistry", "avogadro", "substance", "molar", "molarity", "mass", "gram", "grams",
            "particles", "atoms", "molecules", "reaction", "stoichiometry", "gas", "volume",
            "concentration", "mol", "nacl"
        },
        "non_stem_cues": {
            "skin", "face", "spot", "cheek", "beauty", "rodent", "underground", "animal",
            "mammal", "spy", "secret", "agent", "lawn", "garden", "traitor", "infiltrator"
        },
        "default_caps_stem": False,
        "allow_lowercase": True,
        "allow_plural": True,
        "mapping": {"en": "mole", "hi": "मोल", "kn": "ಮೋಲ್", "ta": "மோல்", "bn": "মোল"},
    },
    "BASE": {
        "stem_cues": {
            "acid", "alkali", "alkaline", "ph", "reaction", "hydroxide", "neutralize",
            "neutralization", "litmus", "logarithm", "exponent", "binary", "decimal", "radix",
            "salt", "indicator", "solution", "chemistry", "ion"
        },
        "non_stem_cues": {
            "baseball", "army", "military", "station", "floor", "headquarters", "bottom",
            "foundation", "camp", "ground", "support", "pillar", "soldier", "soldiers", "patrol"
        },
        "default_caps_stem": False,
        "allow_lowercase": True,
        "allow_plural": True,
        "mapping": {"en": "base", "hi": "क्षार", "kn": "ಪ್ರತ್ಯಾಮ್ಲ", "ta": "காரம்", "bn": "ক্ষার"},
    },
    "SALT": {
        "stem_cues": {
            "acid", "base", "ionic", "neutralization", "compound", "nacl", "crystal", "chloride",
            "sodium", "cation", "anion", "reaction", "solution", "chemistry", "precipitate",
            "electrolysis"
        },
        "non_stem_cues": {
            "food", "cook", "taste", "kitchen", "dining", "sprinkle", "pinch", "pepper",
            "soup", "dish", "flavor", "salad", "recipe"
        },
        "default_caps_stem": False,
        "allow_lowercase": True,
        "allow_plural": True,
        "mapping": {"en": "salt", "hi": "लवण", "kn": "ಲವಣ", "ta": "உப்பு சேர்மம்", "bn": "লবণ"},
    },
    "CELL": {
        "stem_cues": {
            "biology", "tissue", "membrane", "nucleus", "cytoplasm", "mitochondria", "organelle",
            "organism", "electrolysis", "battery", "galvanic", "voltaic", "anode", "cathode",
            "dna", "division", "plant", "microscope", "wall"
        },
        "non_stem_cues": {
            "prison", "jail", "lockup", "police", "criminal", "inmate", "convict", "bars",
            "guard", "excel", "spreadsheet", "row", "column", "mobile", "cellular", "call", "phone"
        },
        "default_caps_stem": False,
        "allow_lowercase": True,
        "allow_plural": True,
        "mapping": {"en": "cell", "hi": "कोशिका", "kn": "ಜೀವಕೋಶ", "ta": "செல்", "bn": "কোষ"},
    },
    "MASS": {
        "stem_cues": {
            "acceleration", "force", "gravity", "weight", "kg", "kilogram", "grams", "inertia",
            "momentum", "newton", "density", "volume", "matter", "physics", "velocity", "motion",
            "energy"
        },
        "non_stem_cues": {
            "church", "christian", "prayer", "sunday", "gathering", "crowd", "people", "media",
            "communication", "priest", "cathedral", "altar"
        },
        "default_caps_stem": False,
        "allow_lowercase": True,
        "mapping": {"en": "mass", "hi": "द्रव्यमान", "kn": "ದ್ರವ್ಯರಾಶಿ", "ta": "நிறை", "bn": "ভর"},
    },
    "WORK": {
        "stem_cues": {
            "force", "displacement", "joule", "joules", "energy", "power", "distance",
            "calculate", "formula", "physics", "mechanics", "motion"
        },
        "non_stem_cues": {
            "job", "office", "career", "employee", "labor", "boss", "salary", "daily",
            "commute", "shift", "company", "colleague", "resume"
        },
        "default_caps_stem": False,
        "allow_lowercase": True,
        "mapping": {"en": "work", "hi": "कार्य", "kn": "ಕಾರ್ಯ", "ta": "வேலை", "bn": "কার্য"},
    },
    "CURRENT": {
        "stem_cues": {
            "voltage", "resistance", "ampere", "amperes", "circuit", "circuits", "ohm", "wire",
            "charge", "flow", "electricity", "electron", "electrons", "conductor", "resistor"
        },
        "non_stem_cues": {
            "affairs", "events", "year", "month", "present", "news", "latest", "ongoing",
            "update", "modern", "today", "date", "situation"
        },
        "default_caps_stem": False,
        "allow_lowercase": True,
        "mapping": {"en": "current", "hi": "विद्युत धारा", "kn": "ವಿದ್ಯುತ್ ಪ್ರವಾಹ", "ta": "மின்னோட்டம்", "bn": "বিদ্যুৎ প্রবাহ"},
    },
    "POWER": {
        "stem_cues": {
            "watt", "watts", "kilowatt", "joule", "energy", "horsepower", "electrical",
            "voltage", "circuit", "generator"
        },
        "non_stem_cues": {
            "political", "politics", "government", "regime", "ruler", "leader", "minister",
            "authority", "influence", "corrupt", "election", "vote"
        },
        "default_caps_stem": False,
        "allow_lowercase": True,
        "mapping": {"en": "power", "hi": "शक्ति", "kn": "ಸಾಮರ್ಥ್ಯ", "ta": "திறன்", "bn": "ক্ষমতা"},
    },
    "AM": {
        "stem_cues": {
            "radio", "frequency", "modulation", "signal", "carrier", "wave", "waves",
            "broadcast", "transmitter", "receiver", "khz", "amplitude", "transmission"
        },
        "non_stem_cues": {
            "morning", "clock", "alarm", "pm", "night", "wake", "student", "boy", "girl",
            "here", "fine", "happy", "ready", "tomorrow", "today"
        },
        "default_caps_stem": True,
        "allow_lowercase": False,
        "mapping": {"en": "A M", "hi": "एएम", "kn": "ಎಎಂ", "ta": "ஏஎம்", "bn": "এএম"},
    },
    "FM": {
        "stem_cues": {
            "radio", "frequency", "modulation", "signal", "carrier", "wave", "waves",
            "broadcast", "transmitter", "receiver", "mhz", "sound", "channel", "station",
            "transmission"
        },
        "non_stem_cues": {
            "finance", "minister", "ministry", "budget", "parliament", "tax"
        },
        "default_caps_stem": True,
        "allow_lowercase": False,
        "mapping": {"en": "F M", "hi": "एफएम", "kn": "ಎಫ್‌ಎಂ", "ta": "எஃப்எம்", "bn": "এফএম"},
    },
}

UNAMBIGUOUS_STEM_ACRONYMS: dict[str, dict[str, str]] = {
    "LED": {"en": "L E D", "hi": "एलईडी", "kn": "ಎಲ್ಇಡಿ", "ta": "எல்இடி", "bn": "এলইডি"},
    "DNA": {"en": "D N A", "hi": "डीएनए", "kn": "ಡಿಎನ್‌ಎ", "ta": "டிஎன்ஏ", "bn": "ডিএনএ"},
    "RNA": {"en": "R N A", "hi": "आरएनए", "kn": "ಆರ್‌ಎನ್‌ಎ", "ta": "ஆர்என்ஏ", "bn": "আরএনএ"},
    "CPU": {"en": "C P U", "hi": "सीपीयू", "kn": "ಸಿಪಿಯು", "ta": "சிபியு", "bn": "সিপিইউ"},
    "GPU": {"en": "G P U", "hi": "जीपीयू", "kn": "ಜಿಪಿಯು", "ta": "ஜிபியு", "bn": "জিপিইউ"},
    "ATP": {"en": "A T P", "hi": "एटीपी", "kn": "ಎಟಿಪಿ", "ta": "ஏடிபி", "bn": "এটিপি"},
    "IIT": {"en": "I I T", "hi": "आईआईटी", "kn": "ಐಐಟಿ", "ta": "ஐಐடி", "bn": "আইআইটি"},
    "CBSE": {"en": "C B S E", "hi": "सीबीएसई", "kn": "ಸಿಬಿಎಸ್‌ಇ", "ta": "சிபிஎஸ்இ", "bn": "সিবিএসই"},
    "NCERT": {"en": "N C E R T", "hi": "एनसीईआरटी", "kn": "ಎನ್‌ಸಿಇಆರ್‌ಟಿ", "ta": "என்சிஇஆர்டி", "bn": "এনসিইআরটি"},
    "ISRO": {"en": "ISRO", "hi": "इसरो", "kn": "ಇಸ್ರೋ", "ta": "இஸ்ரோ", "bn": "ইসরো"},
    "NASA": {"en": "NASA", "hi": "नासा", "kn": "ನಾಸಾ", "ta": "நாசா", "bn": "নাসা"},
    "WHO": {"en": "W H O", "hi": "डब्ल्यूएचओ", "kn": "ಡಬ್ಲ್ಯುಎಚ್‌ಒ", "ta": "டபிள்யுஎச்ஓ", "bn": "ডব্লিউএইচও"},
    "AI": {"en": "A I", "hi": "एआई", "kn": "ಎಐ", "ta": "ஏஐ", "bn": "এআই"},
    "USB": {"en": "U S B", "hi": "यूएसबी", "kn": "ಯುಎಸ್‌ಬಿ", "ta": "யுஎஸ்பி", "bn": "ইউএসবি"},
    "GPS": {"en": "G P S", "hi": "जीपीएस", "kn": "ಜಿಪಿಎಸ್", "ta": "ஜிபிஎஸ்", "bn": "জিপিএস"},
    "URL": {"en": "U R L", "hi": "यूआरएल", "kn": "ಯುಆರ್‌ಎಲ್", "ta": "யுஆர்எல்", "bn": "ইউআরএল"},
    "HTML": {"en": "H T M L", "hi": "एचटीएमएल", "kn": "ಎಚ್‌ಟಿಎಮ್‌ಎಲ್", "ta": "ஹெச்டிஎம்எல்", "bn": "এইচটিএমএল"},
    "EMF": {"en": "E M F", "hi": "ईएमएफ", "kn": "ಇಎಂಎಫ್", "ta": "இஎம்எஃப்", "bn": "ইএমএফ"},
    "RMS": {"en": "R M S", "hi": "आरएमएस", "kn": "ಆರ್‌ಎಂಎಸ್", "ta": "ஆர்எம்எஸ்", "bn": "আরএমএস"},
    "pH": {"en": "p H", "hi": "पीएच", "kn": "ಪಿಎಚ್", "ta": "பிஹெச்", "bn": "পিএইচ"},
    "PH": {"en": "p H", "hi": "पीएच", "kn": "ಪಿಎಚ್", "ta": "பிஹெச்", "bn": "পিএইচ"},
    "STP": {"en": "S T P", "hi": "एसटीपी", "kn": "ಎಸ್‌ಟಿಪಿ", "ta": "எஸ்டிபி", "bn": "এসটিপি"},
    "NTP": {"en": "N T P", "hi": "एनटीपी", "kn": "ಎನ್‌ಟಿಪಿ", "ta": "என்டிபி", "bn": "এনটিপি"},
    "UV": {"en": "U V", "hi": "यूवी", "kn": "ಯುವಿ", "ta": "யுவி", "bn": "ইউভি"},
    "IR": {"en": "I R", "hi": "आईआर", "kn": "ಐಆರ್", "ta": "ஐஆர்", "bn": "আইআর"},
    "ADP": {"en": "A D P", "hi": "एडीपी", "kn": "ಎಡಿಪಿ", "ta": "ஏடிபி", "bn": "এডিপি"},
}

# Unified mapping for backwards compatibility and static lookups
STEM_ACRONYMS: dict[str, dict[str, str]] = {
    term: cfg["mapping"] for term, cfg in STEM_DISAMBIGUATION.items()
}
STEM_ACRONYMS.update(UNAMBIGUOUS_STEM_ACRONYMS)


def expand_stem_acronyms(text: str, lang: str) -> str:
    """Expand STEM abbreviations to native phonetic words using 2A (context) + 2B (orthographic case)."""
    lang_key = lang.split("_")[0]
    out = text

    # Phase 1: Disambiguate and expand ambiguous STEM terms with 2A & 2B checks
    for term, cfg in STEM_DISAMBIGUATION.items():
        plural_pat = r"(?:s|es)?" if cfg.get("allow_plural") else ""
        pat = re.compile(
            rf"\b({term}|{term.capitalize()}){plural_pat}\b",
            re.IGNORECASE if cfg.get("allow_lowercase") else 0,
        )

        def _replace_ambiguous(match: re.Match) -> str:
            token = match.group(0)
            start, end = match.start(), match.end()
            # 2A: Collocation context window (80 chars before and after)
            left_ctx = text[max(0, start - 80):start]
            right_ctx = text[end:min(len(text), end + 80)]
            context_window = f"{left_ctx} {right_ctx}"

            clean_words = set(re.findall(r"[a-zA-Z0-9]+", context_window.lower()))
            stem_hits = len(clean_words.intersection(cfg["stem_cues"]))
            non_stem_hits = len(clean_words.intersection(cfg["non_stem_cues"]))

            # 2B: Case analysis
            is_all_caps = token.isupper() and len(token) > 1

            # 2A: Scoring
            if non_stem_hits > stem_hits:
                return token  # Strong non-STEM context (e.g. King Ram, room AC, skin mole)
            if stem_hits > non_stem_hits:
                if lang_key == "en" and cfg.get("allow_plural") and token.lower().endswith("s"):
                    return token
                return cfg["mapping"].get(lang_key, token)  # Strong STEM context

            # Default to 2B case rule
            if is_all_caps and cfg.get("default_caps_stem", True):
                return cfg["mapping"].get(lang_key, token)

            return token

        out = pat.sub(_replace_ambiguous, out)

    # Phase 2: Expand unambiguous STEM acronyms (strictly case-sensitive \bACRONYM\b)
    for acronym, mapping in UNAMBIGUOUS_STEM_ACRONYMS.items():
        if lang_key in mapping:
            pat = r"\b" + re.escape(acronym) + r"\b"
            out = re.sub(pat, mapping[lang_key], out)

    return out


DISCOURSE_MARKERS: dict[str, list[str]] = {
    "hi": [
        "लेकिन", "किन्तु", "परन्तु", "क्योंकि", "इसलिए", "अतः", "अर्थात",
        "ध्यान दें कि", "ध्यान दें", "उदाहरण के लिए", "इसके अलावा", "वास्तव में", "याद रखें"
    ],
    "kn": [
        "ಆದರೆ", "ಏಕೆಂದರೆ", "ಆದ್ದರಿಂದ", "ಅಂದರೆ", "ಗಮನಿಸಿ",
        "ಉದಾಹರಣೆಗೆ", "ಹಾಗೆಯೇ", "ಮತ್ತೊಂದೆಡೆ", "ನೆನಪಿಡಿ"
    ],
    "ta": [
        "ஆனால்", "ஏனெனில்", "எனவே", "அதாவது", "கவனியுங்கள்",
        "உதாரணமாக", "மேலும்", "மட்டுமல்லாமல்", "நினைவில் கொள்க"
    ],
    "bn": [
        "কিন্তু", "কারণ", "সুতরাং", "অর্থাৎ", "লক্ষ্য করুন",
        "উদাহরণস্বরূপ", "তাছাড়া", "মনে রাখবেন", "বস্তুত"
    ],
}


def insert_breath_pauses(text: str, lang: str) -> str:
    """Insert natural breath pause commas after clause conjunctions and discourse markers.
    
    In TTS models (Kokoro, Meta MMS-TTS/VITS), clause-boundary commas create realistic
    micro-pauses (~100ms) and natural pitch drops, giving synthetic speech a human touch.
    """
    lang_key = lang.split("_")[0]
    markers = DISCOURSE_MARKERS.get(lang_key, [])
    if not markers:
        return text

    out = text
    for marker in sorted(markers, key=len, reverse=True):
        pat = rf"(^|\s){re.escape(marker)}(?=\s|[,.!?;:|\u0964\u0965]|$)"
        out = re.sub(pat, r"\g<1>" + marker + ",", out)


    out = re.sub(r",\s*,+", ",", out)
    out = re.sub(r"\s*,", ", ", out)
    out = re.sub(r",\s*", ", ", out)
    return re.sub(r"\s+", " ", out).strip()


# ---------------------------------------------------------------------------
# 3. clean_for_mms(text, lang) — Pre-TTS MMS sanitation
# ---------------------------------------------------------------------------

SINGLE_LETTER_MAP = {
    "kn": {
        "a": "ಏ", "b": "ಬಿ", "c": "ಸಿ", "d": "ಡಿ", "e": "ಇ", "f": "ಎಫ್", "g": "ಜಿ",
        "h": "ಹೆಚ್", "i": "ಐ", "j": "ಜೆ", "k": "ಕೆ", "l": "ಎಲ್", "m": "ಎಮ್", "n": "ಎನ್",
        "o": "ಓ", "p": "ಪಿ", "q": "ಕ್ಯೂ", "r": "ಆರ್", "s": "ಎಸ್", "t": "ಟಿ", "u": "ಯು",
        "v": "ವಿ", "w": "ಡಬ್ಲ್ಯೂ", "x": "ಎಕ್ಸ್", "y": "ವೈ", "z": "ಝೆಡ್"
    },
    "hi": {
        "a": "ए", "b": "बी", "c": "सी", "d": "डी", "e": "ई", "f": "एफ़", "g": "जी",
        "h": "एच", "i": "आई", "j": "जे", "k": "के", "l": "एल", "m": "एम", "n": "एन",
        "o": "ओ", "p": "पी", "q": "क्यू", "r": "आर", "s": "एस", "t": "टी", "u": "यू",
        "v": "वी", "w": "डब्लू", "x": "एक्स", "y": "वाई", "z": "ज़ेड"
    },
    "ta": {
        "a": "ஏ", "b": "பி", "c": "சி", "d": "டி", "e": "இ", "f": "எஃப்", "g": "ஜி",
        "h": "எச்", "i": "ஐ", "j": "ஜே", "k": "கே", "l": "எல்", "m": "எம்", "n": "என்",
        "o": "ஓ", "p": "பி", "q": "க்யூ", "r": "ஆர்", "s": "எஸ்", "t": "டி", "u": "யு",
        "v": "வி", "w": "டபிள்யு", "x": "எக்ஸ்", "y": "ஒய்", "z": "இசட்"
    },
    "bn": {
        "a": "এ", "b": "বি", "c": "সি", "d": "ডি", "e": "ই", "f": "এফ", "g": "জি",
        "h": "এইচ", "i": "আই", "j": "জে", "k": "কে", "l": "এল", "m": "এম", "n": "এন",
        "o": "ও", "p": "পি", "q": "কিউ", "r": "আর", "s": "এস", "t": "টি", "u": "ইউ",
        "v": "ভি", "w": "ডাব্লিউ", "x": "এক্স", "y": "ওয়াই", "z": "জেড"
    }
}

def clean_for_mms(text: str, lang: str = "kn") -> str:
    """Clean and sanitize text before passing to Meta's MMS-TTS model.
    
    Guarantees:
      1. Expands STEM acronyms (LED -> ಎಲ್ಇಡಿ / এলইডি) for native phonetics.
      2. Zero ASCII digits (0-9) remain in the string.
      3. No raw math operators (=, +, -, *, /, Ω, %) that MMS drops.
      4. Expands standalone units (V, A, W, Ω, %, °C) to native words.
      5. Punctuation is normalized to natural pause markers (commas, periods).
      6. Injects clause-boundary micro-pauses for human-like breath rhythm.
      7. Strips unsupported symbols and brackets ([] {} () <> _ ^ ` ~).
    """
    # 0. Expand STEM acronyms first so characters don't get garbled or dropped
    out = expand_stem_acronyms(text, lang)

    # Normalize hyphenated compound words (e.g. fast-charging -> fast charging, forty-six -> forty six)
    out = re.sub(r"(?<=[^\s\d\(\)\[\]\{\}\<\>])-(?=[^\s\d\(\)\[\]\{\}\<\>])", " ", out)

    # 1. Expand units and symbols to native script words first
    if lang in ("kn", "kan_Knda"):
        out = re.sub(r"°\s*C", " ಡಿಗ್ರಿ ಸೆಲ್ಸಿಯಸ್ ", out)
        out = re.sub(r"°\s*F", " ಡಿಗ್ರಿ ಫ್ಯಾರನ್‌ಹೀಟ್ ", out)
        out = re.sub(r"Ω", " ಓಮ್ ", out)
        out = re.sub(r"\bOhm'?s?\b", "ಓಮ್", out, flags=re.IGNORECASE)
        out = re.sub(r"\bVolts?\b", "ವೋಲ್ಟ್", out, flags=re.IGNORECASE)
        out = re.sub(r"\bAmperes?\b|\bAmps?\b", "ಆಂಪಿಯರ್", out, flags=re.IGNORECASE)
        out = re.sub(r"\bWatts?\b", "ವ್ಯಾಟ್", out, flags=re.IGNORECASE)
        out = re.sub(r"\bHertz\b", "ಹರ್ಟ್ಜ್", out, flags=re.IGNORECASE)
        out = re.sub(r"\bkHz\b|\bkilohertz\b", "ಕಿಲೋಹರ್ಟ್ಜ್", out, flags=re.IGNORECASE)
        out = re.sub(r"\bfps\b", "ಫ್ರೇಮ್ ಪ್ರತಿ ಸೆಕೆಂಡ್", out, flags=re.IGNORECASE)
        out = re.sub(r"\bseconds?\b|\bsecs?\b", "ಸೆಕೆಂಡ್", out, flags=re.IGNORECASE)
        out = re.sub(r"\bmeters?\b", "ಮೀಟರ್", out, flags=re.IGNORECASE)
        out = re.sub(r"\bJoules?\b", "ಜೂಲ್", out, flags=re.IGNORECASE)
        out = re.sub(r"\bNewtons?\b", "ನ್ಯೂಟನ್", out, flags=re.IGNORECASE)
        out = re.sub(r"\bCurrent\b", "ಕರೆಂಟ್", out, flags=re.IGNORECASE)
        out = re.sub(r"\bVoltage\b", "ವೋಲ್ಟೇಜ್", out, flags=re.IGNORECASE)
        out = re.sub(r"\bResistance\b", "ಪ್ರತಿರೋಧ", out, flags=re.IGNORECASE)
        out = re.sub(r"\bResistors?\b", "ಪ್ರತಿರೋಧಕ", out, flags=re.IGNORECASE)
        out = re.sub(r"\bCircuits?\b", "ಸರ್ಕ್ಯೂಟ್", out, flags=re.IGNORECASE)
        out = re.sub(r"\bBatter(?:y|ies)\b", "ಬ್ಯಾಟರಿ", out, flags=re.IGNORECASE)
        out = re.sub(r"%", " ಪ್ರತಿಶತ ", out)
        out = re.sub(r"\bV\b", "ವೋಲ್ಟ್", out)
        out = re.sub(r"\bA\b", "ಆಂಪಿಯರ್", out)
        out = re.sub(r"\bW\b", "ವ್ಯಾಟ್", out)
        out = re.sub(r"\bHz\b", "ಹರ್ಟ್ಜ್", out)
        out = re.sub(r"\s*=\s*", " ಸಮಾನ ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " ಗುಣಿಸು ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " ಭಾಗಿಸು ", out)
        out = re.sub(r"\s*\+\s*", " ಪ್ಲಸ್ ", out)
        out = re.sub(r"\s*-\s*", " ಮೈನಸ್ ", out)
    elif lang in ("hi", "hin_Deva"):
        out = re.sub(r"°\s*C", " डिग्री सेल्सियस ", out)
        out = re.sub(r"°\s*F", " डिग्री फ़ारेनहाइट ", out)
        out = re.sub(r"Ω", " ओम ", out)
        out = re.sub(r"\bOhm'?s?\b", "ओम", out, flags=re.IGNORECASE)
        out = re.sub(r"\bVolts?\b", "वोल्ट", out, flags=re.IGNORECASE)
        out = re.sub(r"\bAmperes?\b|\bAmps?\b", "एम्पीयर", out, flags=re.IGNORECASE)
        out = re.sub(r"\bWatts?\b", "वाट", out, flags=re.IGNORECASE)
        out = re.sub(r"\bHertz\b", "हर्ट्ज़", out, flags=re.IGNORECASE)
        out = re.sub(r"\bkHz\b|\bkilohertz\b", "किलोहर्ट्ज़", out, flags=re.IGNORECASE)
        out = re.sub(r"\bfps\b", "फ्रेम प्रति सेकंड", out, flags=re.IGNORECASE)
        out = re.sub(r"\bseconds?\b|\bsecs?\b", "सेकंड", out, flags=re.IGNORECASE)
        out = re.sub(r"\bmeters?\b", "मीटर", out, flags=re.IGNORECASE)
        out = re.sub(r"\bJoules?\b", "जूल", out, flags=re.IGNORECASE)
        out = re.sub(r"\bNewtons?\b", "न्यूटन", out, flags=re.IGNORECASE)
        out = re.sub(r"\bCurrent\b", "करंट", out, flags=re.IGNORECASE)
        out = re.sub(r"\bVoltage\b", "वोल्टेज", out, flags=re.IGNORECASE)
        out = re.sub(r"\bResistance\b", "प्रतिरोध", out, flags=re.IGNORECASE)
        out = re.sub(r"\bResistors?\b", "प्रतिरोधक", out, flags=re.IGNORECASE)
        out = re.sub(r"\bCircuits?\b", "सर्किट", out, flags=re.IGNORECASE)
        out = re.sub(r"\bBatter(?:y|ies)\b", "बैटरी", out, flags=re.IGNORECASE)
        out = re.sub(r"%", " प्रतिशत ", out)
        out = re.sub(r"\bV\b", "वोल्ट", out)
        out = re.sub(r"\bA\b", "एम्पीयर", out)
        out = re.sub(r"\bW\b", "वाट", out)
        out = re.sub(r"\bHz\b", "हर्ट्ज़", out)
        out = re.sub(r"\s*=\s*", " बराबर ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " गुणा ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " भागाकार ", out)
        out = re.sub(r"\s*\+\s*", " प्लस ", out)
        out = re.sub(r"\s*-\s*", " माइनस ", out)
    elif lang in ("ta", "tam_Taml"):
        out = re.sub(r"°\s*C", " டிகிரி செல்சியஸ் ", out)
        out = re.sub(r"°\s*F", " டிகிரி பாரன்ஹீட் ", out)
        out = re.sub(r"Ω", " ஓம் ", out)
        out = re.sub(r"\bOhm'?s?\b", "ஓம்", out, flags=re.IGNORECASE)
        out = re.sub(r"\bVolts?\b", "வோல்ட்", out, flags=re.IGNORECASE)
        out = re.sub(r"\bAmperes?\b|\bAmps?\b", "ஆம்பியர்", out, flags=re.IGNORECASE)
        out = re.sub(r"\bWatts?\b", "வாட்", out, flags=re.IGNORECASE)
        out = re.sub(r"\bHertz\b", "ஹெர்ட்ஸ்", out, flags=re.IGNORECASE)
        out = re.sub(r"\bkHz\b|\bkilohertz\b", "கிலோஹெர்ட்ஸ்", out, flags=re.IGNORECASE)
        out = re.sub(r"\bfps\b", "பிரேம் பர் விநாடி", out, flags=re.IGNORECASE)
        out = re.sub(r"\bseconds?\b|\bsecs?\b", "வினாடிகள்", out, flags=re.IGNORECASE)
        out = re.sub(r"\bmeters?\b", "மீட்டர்", out, flags=re.IGNORECASE)
        out = re.sub(r"\bJoules?\b", "ஜூல்", out, flags=re.IGNORECASE)
        out = re.sub(r"\bNewtons?\b", "நியூட்டன்", out, flags=re.IGNORECASE)
        out = re.sub(r"\bCurrent\b", "மின்னோட்டம்", out, flags=re.IGNORECASE)
        out = re.sub(r"\bVoltage\b", "மின்னழுத்தம்", out, flags=re.IGNORECASE)
        out = re.sub(r"\bResistance\b", "மின்தடை", out, flags=re.IGNORECASE)
        out = re.sub(r"\bResistors?\b", "மின்தடையம்", out, flags=re.IGNORECASE)
        out = re.sub(r"\bCircuits?\b", "மின்சுற்று", out, flags=re.IGNORECASE)
        out = re.sub(r"\bBatter(?:y|ies)\b", "பேட்டரி", out, flags=re.IGNORECASE)
        out = re.sub(r"%", " சதவீதம் ", out)
        out = re.sub(r"\bV\b", "வோல்ட்", out)
        out = re.sub(r"\bA\b", "ஆம்பியர்", out)
        out = re.sub(r"\bW\b", "வாட்", out)
        out = re.sub(r"\bHz\b", "ஹெர்ட்ஸ்", out)
        out = re.sub(r"\s*=\s*", " சமம் ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " பெருக்கல் ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " வகுத்தல் ", out)
        out = re.sub(r"\s*\+\s*", " கூட்டல் ", out)
        out = re.sub(r"\s*-\s*", " கழித்தல் ", out)
    elif lang in ("bn", "ben_Beng"):
        out = re.sub(r"°\s*C", " ডিগ্রি সেলসিয়াস ", out)
        out = re.sub(r"°\s*F", " ডিগ্রি ফারেনহাইট ", out)
        out = re.sub(r"Ω", " ওহম ", out)
        out = re.sub(r"\bOhm'?s?\b", "ওহম", out, flags=re.IGNORECASE)
        out = re.sub(r"\bVolts?\b", "ভোল্ট", out, flags=re.IGNORECASE)
        out = re.sub(r"\bAmperes?\b|\bAmps?\b", "অ্যাম্পিয়ার", out, flags=re.IGNORECASE)
        out = re.sub(r"\bWatts?\b", "ওয়াট", out, flags=re.IGNORECASE)
        out = re.sub(r"\bHertz\b", "হার্টজ", out, flags=re.IGNORECASE)
        out = re.sub(r"\bkHz\b|\bkilohertz\b", "কিলোহাটর্জ", out, flags=re.IGNORECASE)
        out = re.sub(r"\bfps\b", "ফ্রেম প্রতি সেকেন্ড", out, flags=re.IGNORECASE)
        out = re.sub(r"\bseconds?\b|\bsecs?\b", "সেকেন্ড", out, flags=re.IGNORECASE)
        out = re.sub(r"\bmeters?\b", "মিটার", out, flags=re.IGNORECASE)
        out = re.sub(r"\bJoules?\b", "জুল", out, flags=re.IGNORECASE)
        out = re.sub(r"\bNewtons?\b", "নিউটন", out, flags=re.IGNORECASE)
        out = re.sub(r"\bCurrent\b", "কারেন্ট", out, flags=re.IGNORECASE)
        out = re.sub(r"\bVoltage\b", "ভোল্টেজ", out, flags=re.IGNORECASE)
        out = re.sub(r"\bResistance\b", "প্রতিরোধ", out, flags=re.IGNORECASE)
        out = re.sub(r"\bResistors?\b", "প্রতিরোধক", out, flags=re.IGNORECASE)
        out = re.sub(r"\bCircuits?\b", "সার্কিট", out, flags=re.IGNORECASE)
        out = re.sub(r"\bBatter(?:y|ies)\b", "ব্যাটারি", out, flags=re.IGNORECASE)
        out = re.sub(r"%", " শতাংশ ", out)
        out = re.sub(r"\bV\b", "ভোল্ট", out)
        out = re.sub(r"\bA\b", "অ্যাম্পিয়ার", out)
        out = re.sub(r"\bW\b", "ওয়াট", out)
        out = re.sub(r"\bHz\b", "হার্টজ", out)
        out = re.sub(r"\s*=\s*", " সমান ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " গুণ ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " ভাগ ", out)
        out = re.sub(r"\s*\+\s*", " প্লাস ", out)
        out = re.sub(r"\s*-\s*", " মাইনাস ", out)
    else:
        out = re.sub(r"°\s*C", " degrees Celsius ", out)
        out = re.sub(r"°\s*F", " degrees Fahrenheit ", out)
        out = re.sub(r"Ω", " ohms ", out)
        out = re.sub(r"%", " percent ", out)
        out = re.sub(r"\bV\b", "volts", out)
        out = re.sub(r"\bA\b", "amperes", out)
        out = re.sub(r"\bW\b", "watts", out)
        out = re.sub(r"\bHz\b", "hertz", out)
        out = re.sub(r"\s*=\s*", " equals ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " times ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " divided by ", out)
        out = re.sub(r"\s*\+\s*", " plus ", out)
        out = re.sub(r"\s*-\s*", " minus ", out)

    # 1B. Expand any remaining single Latin letters to native script phonetics
    lang_key = lang.split("_")[0]
    if lang_key in SINGLE_LETTER_MAP:
        letter_dict = SINGLE_LETTER_MAP[lang_key]
        out = re.sub(
            r"\b([a-zA-Z])\b",
            lambda m: letter_dict.get(m.group(1).lower(), m.group(1)),
            out,
        )

    # 2. Expand any residual digits
    out = fix_residual_digits(out, lang)

    # 3. Safety pass: if any digit still remains, replace it
    if re.search(r"\d", out):
        if lang in ("kn", "kan_Knda"):
            out = re.sub(r"\b\d+\b", lambda m: kannada_number_to_words(int(m.group(0))), out)
        elif lang in ("hi", "hin_Deva"):
            out = re.sub(r"\b\d+\b", lambda m: hindi_number_to_words(int(m.group(0))), out)
        elif lang in ("ta", "tam_Taml"):
            out = re.sub(r"\b\d+\b", lambda m: tamil_number_to_words(int(m.group(0))), out)
        elif lang in ("bn", "ben_Beng"):
            out = re.sub(r"\b\d+\b", lambda m: bengali_number_to_words(int(m.group(0))), out)
        else:
            out = re.sub(r"\b\d+\b", lambda m: english_number_to_words(int(m.group(0))), out)

    # 4. Ingest breath pause micro-commas for natural speech cadence
    out = insert_breath_pauses(out, lang)

    # 5. Normalize punctuation to pauses
    out = re.sub(r"[\:;\|\/]+", ", ", out)
    out = re.sub(r"[\(\)\[\]\{\}\<\>\"\'`~_]+", " ", out)
    out = re.sub(r"\s*-\s*", " ", out)

    # 6. Collapse spaces & trim
    out = re.sub(r"\s+", " ", out).strip()
    out = re.sub(r",\s*,+", ",", out)
    return out.strip(" ,-")


def count_ascii_digits(text: str) -> int:
    """Return count of ASCII digits (0-9) present in text."""
    return len(re.findall(r"\d", text))


def has_ascii_digits(text: str) -> bool:
    """Check if any ASCII digit (0-9) is present in text."""
    return bool(re.search(r"\d", text))


def expand_numbers_and_symbols(text: str, lang: str) -> str:
    """Expand numbers, scientific units, and mathematical symbols into spoken words."""
    out = expand_stem_acronyms(text, lang)
    if lang in ("kn", "kan_Knda"):
        # Math operators
        out = re.sub(r"\s*=\s*", " ಸಮಾನ ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " ಗುಣಿಸು ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " ಭಾಗಿಸು ", out)
        out = re.sub(r"\s*\+\s*", " ಪ್ಲಸ್ ", out)
        out = re.sub(r"\s*-\s*", " ಮೈನಸ್ ", out)
        # Units
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:V|Volts?)\b", r"\1 ವೋಲ್ಟ್", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:Ω|Ohms?)\b", r"\1 ಓಮ್", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:A|Amperes?|Amps?)\b", r"\1 ಆಂಪಿಯರ್", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:W|Watts?)\b", r"\1 ವ್ಯಾಟ್", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:Hz|Hertz)\b", r"\1 ಹರ್ಟ್ಜ್", out)
        out = re.sub(r"°\s*C", "ಡಿಗ್ರಿ ಸೆಲ್ಸಿಯಸ್", out)
        out = re.sub(r"°\s*F", "ಡಿಗ್ರಿ ಫ್ಯಾರನ್‌ಹೀಟ್", out)
        out = re.sub(r"%", "ಪ್ರತಿಶತ", out)
        # Residual symbols with words
        out = fix_residual_digits(out, "kn")
    elif lang in ("hi", "hin_Deva"):
        out = re.sub(r"\s*=\s*", " बराबर ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " गुणा ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " भागाकार ", out)
        out = re.sub(r"\s*\+\s*", " प्लस ", out)
        out = re.sub(r"\s*-\s*", " माइनस ", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:V|Volts?)\b", r"\1 वोल्ट", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:Ω|Ohms?)\b", r"\1 ओम", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:A|Amperes?|Amps?)\b", r"\1 एम्पीयर", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:W|Watts?)\b", r"\1 वाट", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:Hz|Hertz)\b", r"\1 हर्ट्ज़", out)
        out = re.sub(r"°\s*C", "डिग्री सेल्सियस", out)
        out = re.sub(r"°\s*F", "डिग्री फ़ारेनहाइट", out)
        out = re.sub(r"%", "प्रतिशत", out)
        out = fix_residual_digits(out, "hi")
    elif lang in ("ta", "tam_Taml"):
        out = re.sub(r"\s*=\s*", " சமம் ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " பெருக்கல் ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " வகுத்தல் ", out)
        out = re.sub(r"\s*\+\s*", " கூட்டல் ", out)
        out = re.sub(r"\s*-\s*", " கழித்தல் ", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:V|Volts?)\b", r"\1 வோல்ட்", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:Ω|Ohms?)\b", r"\1 ஓம்", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:A|Amperes?|Amps?)\b", r"\1 ஆம்பியர்", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:W|Watts?)\b", r"\1 வாட்", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:Hz|Hertz)\b", r"\1 ஹெர்ட்ஸ்", out)
        out = re.sub(r"°\s*C", "டிகிரி செல்சியஸ்", out)
        out = re.sub(r"°\s*F", "டிகிரி பாரன்ஹீட்", out)
        out = re.sub(r"%", "சதவீதம்", out)
        out = fix_residual_digits(out, "ta")
    elif lang in ("bn", "ben_Beng"):
        out = re.sub(r"\s*=\s*", " সমান ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " গুণ ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " ভাগ ", out)
        out = re.sub(r"\s*\+\s*", " প্লাস ", out)
        out = re.sub(r"\s*-\s*", " মাইনাস ", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:V|Volts?)\b", r"\1 ভোল্ট", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:Ω|Ohms?)\b", r"\1 ওহম", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:A|Amperes?|Amps?)\b", r"\1 অ্যাম্পিয়ার", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:W|Watts?)\b", r"\1 ওয়াট", out)
        out = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:Hz|Hertz)\b", r"\1 হার্টজ", out)
        out = re.sub(r"°\s*C", "ডিগ্রি সেলসিয়াস", out)
        out = re.sub(r"°\s*F", "ডিগ্রি ফারেনহাইট", out)
        out = re.sub(r"%", "শতাংশ", out)
        out = fix_residual_digits(out, "bn")
    else:
        out = speak_en(text)
        out = fix_residual_digits(out, "en")

    return re.sub(r"\s+", " ", out).strip()

