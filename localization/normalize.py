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


def telugu_number_to_words(n: int) -> str:
    """Convert an integer (0 to 9999999) to Telugu words."""
    if n == 0:
        return "సున్నా"
    if n < 0:
        return "మైనస్ " + telugu_number_to_words(abs(n))

    units = ["", "ఒకటి", "రెండు", "మూడు", "నాలుగు", "ఐదు", "ఆరు", "ఏడు", "ఎనిమిది", "తొమ్మిది"]
    teens = [
        "పది", "పదకొండు", "పన్నెండు", "పదమూడు", "పద్నాలుగు",
        "పదిహేను", "పదహారు", "పదిహేడు", "పద్దెనిమిది", "పంతొమ్మిది"
    ]
    tens_exact = ["", "", "ఇరవై", "ముప్పై", "నలభై", "యాభై", "అరవై", "డెబ్బై", "ఎనభై", "తొంబై"]
    tens_comb = ["", "", "ఇరవై ", "ముప్పై ", "నలభై ", "యాభై ", "అరవై ", "డెబ్బై ", "ఎనభై ", "తొంబై "]
    hundreds_exact = ["", "వంద", "రెండు వందలు", "మూడు వందలు", "నాలుగు వందలు", "ఐదు వందలు", "ఆరు వందలు", "ఏడు వందలు", "ఎనిమిది వందలు", "తొమ్మిది వందలు"]
    hundreds_comb = ["", "వందల ", "రెండు వందల ", "మూడు వందల ", "నాలుగు వందల ", "ఐదు వందల ", "ఆరు వందల ", "ఏడు వందల ", "ఎనిమిది వందల ", "తొమ్మిది వందల "]

    if n < 10:
        return units[n]
    if n < 20:
        return teens[n - 10]
    if n < 100:
        ten, rem = n // 10, n % 10
        return tens_exact[ten] if rem == 0 else (tens_comb[ten] + units[rem])
    if n < 1000:
        h, rem = n // 100, n % 100
        return hundreds_exact[h] if rem == 0 else (hundreds_comb[h] + telugu_number_to_words(rem))
    if n < 100000:
        th, rem = n // 1000, n % 1000
        if th == 1:
            prefix = "వెయ్యి " if rem else "వెయ్యి"
        else:
            th_w = telugu_number_to_words(th)
            prefix = f"{th_w} వేల " if rem else f"{th_w} వేలు"
        return prefix if rem == 0 else (prefix + telugu_number_to_words(rem))
    if n < 10000000:
        lakh, rem = n // 100000, n % 100000
        lakh_w = telugu_number_to_words(lakh)
        prefix = f"{lakh_w} లక్షల " if rem else f"{lakh_w} లక్ష"
        return prefix if rem == 0 else (prefix + telugu_number_to_words(rem))

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
        elif lang in ("te", "tel_Telu"):
            int_w = telugu_number_to_words(int_part)
            dec_w = " ".join(telugu_number_to_words(int(d)) for d in dec_digits)
            return f"{int_w} బిందువు {dec_w}"
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

    elif lang in ("te", "tel_Telu"):
        out = re.sub(r"(\b\d+\b)\s*%", r"\1 శాతం", out)
        out = re.sub(r"°\s*C", "డిగ్రీ సెల్సియస్", out)
        out = re.sub(r"°\s*F", "డిగ్రీ ఫారెన్‌హీట్", out)
        out = re.sub(r"Ω", "ఓమ్", out)
        out = re.sub(r"\s*=\s*", " సమానం ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " గుణకారం ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " భాగహారం ", out)
        out = re.sub(r"\s*\+\s*", " ప్లస్ ", out)
        out = re.sub(r"\s*-\s*", " మైనస్ ", out)
        out = re.sub(r"\s*→\s*", " దారి తీస్తుంది ", out)

        def _replace_int_te(m: re.Match) -> str:
            return telugu_number_to_words(int(m.group(0)))

        out = re.sub(r"\b\d+\b", _replace_int_te, out)

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
# 3. clean_for_mms(text, lang) — Pre-TTS MMS sanitation
# ---------------------------------------------------------------------------
def clean_for_mms(text: str, lang: str = "kn") -> str:
    """Clean and sanitize text before passing to Meta's MMS-TTS model.
    
    Guarantees:
      1. Zero ASCII digits (0-9) remain in the string.
      2. No raw math operators (=, +, -, *, /, Ω, %) that MMS drops.
      3. Expands standalone units (V, A, W, Ω, %, °C) to native words.
      4. Punctuation is normalized to natural pause markers (commas, periods).
      5. Strips unsupported symbols and brackets ([] {} () <> _ ^ ` ~).
    """
    # 1. Expand units and symbols to native script words first
    out = text
    if lang in ("kn", "kan_Knda"):
        out = re.sub(r"°\s*C", " ಡಿಗ್ರಿ ಸೆಲ್ಸಿಯಸ್ ", out)
        out = re.sub(r"°\s*F", " ಡಿಗ್ರಿ ಫ್ಯಾರನ್‌ಹೀಟ್ ", out)
        out = re.sub(r"Ω", " ಓಮ್ ", out)
        out = re.sub(r"%", " ಪ್ರತಿಶತ ", out)
        out = re.sub(r"\bV\b", "ವೋಲ್ಟ್", out)
        out = re.sub(r"\bA\b", "ಆಂಪಿಯರ್", out)
        out = re.sub(r"\bW\b", "ವ್ಯಾಟ್", out)
        out = re.sub(r"\bHz\b", "ಹರ್ಟ್ಜ್", out)
        out = re.sub(r"\bkHz\b", "ಕಿಲೋಹರ್ಟ್ಜ್", out)
        out = re.sub(r"\bfps\b", "ಫ್ರೇಮ್ ಪ್ರತಿ ಸೆಕೆಂಡ್", out)
        out = re.sub(r"\s*=\s*", " ಸಮಾನ ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " ಗುಣಿಸು ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " ಭಾಗಿಸು ", out)
        out = re.sub(r"\s*\+\s*", " ಪ್ಲಸ್ ", out)
        out = re.sub(r"\s*-\s*", " ಮೈನಸ್ ", out)
    elif lang in ("hi", "hin_Deva"):
        out = re.sub(r"°\s*C", " डिग्री सेल्सियस ", out)
        out = re.sub(r"°\s*F", " डिग्री फ़ारेनहाइट ", out)
        out = re.sub(r"Ω", " ओम ", out)
        out = re.sub(r"%", " प्रतिशत ", out)
        out = re.sub(r"\bV\b", "वोल्ट", out)
        out = re.sub(r"\bA\b", "एम्पीयर", out)
        out = re.sub(r"\bW\b", "वाट", out)
        out = re.sub(r"\bHz\b", "हर्ट्ज़", out)
        out = re.sub(r"\bkHz\b", "किलोहर्ट्ज़", out)
        out = re.sub(r"\bfps\b", "फ्रेम प्रति सेकंड", out)
        out = re.sub(r"\s*=\s*", " बराबर ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " गुणा ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " भागाकार ", out)
        out = re.sub(r"\s*\+\s*", " प्लस ", out)
        out = re.sub(r"\s*-\s*", " माइनस ", out)
    elif lang in ("ta", "tam_Taml"):
        out = re.sub(r"°\s*C", " டிகிரி செல்சியஸ் ", out)
        out = re.sub(r"°\s*F", " டிகிரி பாரன்ஹீட் ", out)
        out = re.sub(r"Ω", " ஓம் ", out)
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
    elif lang in ("te", "tel_Telu"):
        out = re.sub(r"°\s*C", " డిగ్రీ సెల్సియస్ ", out)
        out = re.sub(r"°\s*F", " డిగ్రీ ఫారెన్‌హీట్ ", out)
        out = re.sub(r"Ω", " ఓమ్ ", out)
        out = re.sub(r"%", " శాతం ", out)
        out = re.sub(r"\bV\b", "వోల్ట్", out)
        out = re.sub(r"\bA\b", "ఆంపియర్", out)
        out = re.sub(r"\bW\b", "వాట్", out)
        out = re.sub(r"\bHz\b", "హెర్ట్జ్", out)
        out = re.sub(r"\s*=\s*", " సమానం ", out)
        out = re.sub(r"\s*(?:×|\*)\s*", " గుణకారం ", out)
        out = re.sub(r"\s*(?:÷|\/)\s*", " భాగహారం ", out)
        out = re.sub(r"\s*\+\s*", " ప్లస్ ", out)
        out = re.sub(r"\s*-\s*", " మైనస్ ", out)
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
        elif lang in ("te", "tel_Telu"):
            out = re.sub(r"\b\d+\b", lambda m: telugu_number_to_words(int(m.group(0))), out)
        else:
            out = re.sub(r"\b\d+\b", lambda m: english_number_to_words(int(m.group(0))), out)

    # 4. Normalize punctuation to pauses
    out = re.sub(r"[\:;\|\/]+", ", ", out)
    out = re.sub(r"[\(\)\[\]\{\}\<\>\"\'`~_]+", " ", out)
    out = re.sub(r"\s*-\s*", " ", out)

    # 5. Collapse spaces & trim
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
    out = text
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
    else:
        out = speak_en(text)
        out = fix_residual_digits(out, "en")

    return re.sub(r"\s+", " ", out).strip()

