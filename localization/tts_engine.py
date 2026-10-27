"""localization/tts_engine.py — Dual-Engine Offline TTS (Kokoro-82M + MMS-TTS).

Features:
  - Kokoro-82M for English ('a', af_heart) and Hindi ('h', hf_alpha).
  - Meta MMS-TTS for Kannada ('facebook/mms-tts-kan', VitsModel).
  - Kannada/Hindi/English number-to-words & symbol expansion (prevents MMS-TTS dropping digits).
  - Missing espeak-ng guard for Windows (prevents Kokoro-Hindi crashes).
  - Deterministic duration prediction: torch.manual_seed(42) before forward passes.
  - Zero double-padding: 0.35s tail silence is included in the audio, and the measured
    audio length directly forms scene duration in manifest.json.
  - Standardized 24,000 Hz sample rate output.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import struct
import wave
from pathlib import Path
from typing import Any, Sequence

if os.environ.get("BVT_HF_HOME"):
    os.environ.setdefault("HF_HOME", os.environ["BVT_HF_HOME"])

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import torch
    from transformers import AutoTokenizer, VitsModel
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    from kokoro import KPipeline
    HAS_KOKORO = True
except ImportError:
    HAS_KOKORO = False

try:
    from scipy.signal import resample_poly
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

from localization.normalize import clean_for_mms, tamil_number_to_words, bengali_number_to_words

TARGET_SR = 24000
TAIL_PAD_SEC = 0.35
WORDS_PER_SEC = 2.3

# ---------------------------------------------------------------------------
# Number-to-Words & Math Symbol Expansion
# ---------------------------------------------------------------------------
def kannada_number_to_words(n: int) -> str:
    """Convert an integer (0 to 999999) to Kannada words."""
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
    """Convert an integer (0 to 999999) to Hindi words."""
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
    """Convert an integer (0 to 999999) to English words."""
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


def expand_numbers_and_symbols(text: str, lang: str) -> str:
    """Expand numbers and mathematical symbols into spoken words for the given language.
    
    This is essential for MMS-TTS (Kannada) which silently drops ASCII digits (0-9) and math symbols.
    """
    out = text

    # Expand decimals e.g. 0.35, 9.8
    def _replace_decimal(match: re.Match) -> str:
        int_part = int(match.group(1))
        dec_str = match.group(2)
        if lang == "kn":
            int_words = kannada_number_to_words(int_part)
            dec_words = " ".join(kannada_number_to_words(int(d)) for d in dec_str)
            return f"{int_words} ಬಿಂದು {dec_words}"
        elif lang in ("hi", "hin_Deva"):
            int_words = hindi_number_to_words(int_part)
            dec_words = " ".join(hindi_number_to_words(int(d)) for d in dec_str)
            return f"{int_words} दशमलव {dec_words}"
        elif lang in ("ta", "tam_Taml"):
            int_words = tamil_number_to_words(int_part)
            dec_words = " ".join(tamil_number_to_words(int(d)) for d in dec_str)
            return f"{int_words} புள்ளி {dec_words}"
        elif lang in ("bn", "ben_Beng"):
            int_words = bengali_number_to_words(int_part)
            dec_words = " ".join(bengali_number_to_words(int(d)) for d in dec_str)
            return f"{int_words} দশমিক {dec_words}"
        else:
            int_words = english_number_to_words(int_part)
            dec_words = " ".join(english_number_to_words(int(d)) for d in dec_str)
            return f"{int_words} point {dec_words}"

    out = re.sub(r"\b(\d+)\.(\d+)\b", _replace_decimal, out)

    # Expand symbols and units
    if lang == "kn":
        symbol_map = [
            (r"\b(\d+)\s*(?:Ω|Ohms?|ಓಮ್)\b", r"\1 ಓಮ್"),
            (r"\b(\d+)\s*(?:V|Volts?|ವೋಲ್ಟ್)\b", r"\1 ವೋಲ್ಟ್"),
            (r"\b(\d+)\s*(?:A|Amperes?|ಆಂಪಿಯರ್)\b", r"\1 ಆಂಪಿಯರ್"),
            (r"\b(\d+)\s*(?:W|Watts?|ವ್ಯಾಟ್)\b", r"\1 ವ್ಯಾಟ್"),
            (r"\b(\d+)\s*(?:Hz|Hertz|ಹರ್ಟ್ಜ್)\b", r"\1 ಹರ್ಟ್ಜ್"),
            (r"\b(\d+)\s*%", r"\1 ಪ್ರತಿಶತ"),
            (r"\b(\d+)\s*fps\b", r"\1 ಫ್ರೇಮ್ ಪ್ರತಿ ಸೆಕೆಂಡ್"),
            (r"\b(\d+)\s*(?:s|sec|ಸೆಕೆಂಡ್)\b", r"\1 ಸೆಕೆಂಡ್"),
            (r"\s*=\s*", " ಸಮಾನ "),
            (r"\s*(?:×|\*)\s*", " ಗುಣಿಸು "),
            (r"\s*(?:÷|\/)\s*", " ಭಾಗಿಸು "),
            (r"\s*\+\s*", " ಪ್ಲಸ್ "),
            (r"\s*-\s*", " ಮೈನಸ್ "),
            (r"\s*→\s*", " ಕಾರಣವಾಗುತ್ತದೆ "),
        ]
        for pat, repl in symbol_map:
            out = re.sub(pat, repl, out)

        # Expand remaining integer digits
        def _replace_int_kn(m: re.Match) -> str:
            return kannada_number_to_words(int(m.group(0)))

        out = re.sub(r"\b\d+\b", _replace_int_kn, out)

    elif lang == "hi":
        symbol_map = [
            (r"\b(\d+)\s*(?:Ω|Ohms?|ओम)\b", r"\1 ओम"),
            (r"\b(\d+)\s*(?:V|Volts?|वोल्ट)\b", r"\1 वोल्ट"),
            (r"\b(\d+)\s*(?:A|Amperes?|एम्पीयर)\b", r"\1 एम्पीयर"),
            (r"\b(\d+)\s*(?:W|Watts?|वाट)\b", r"\1 वाट"),
            (r"\b(\d+)\s*(?:Hz|Hertz|हर्ट्ज़)\b", r"\1 हर्ट्ज़"),
            (r"\b(\d+)\s*%", r"\1 प्रतिशत"),
            (r"\b(\d+)\s*fps\b", r"\1 फ्रेम प्रति सेकंड"),
            (r"\b(\d+)\s*(?:s|sec|सेकंड)\b", r"\1 सेकंड"),
            (r"\s*=\s*", " बराबर "),
            (r"\s*(?:×|\*)\s*", " गुणा "),
            (r"\s*(?:÷|\/)\s*", " भागाकार "),
            (r"\s*\+\s*", " प्लस "),
            (r"\s*-\s*", " माइनस "),
            (r"\s*→\s*", " की ओर "),
        ]
        for pat, repl in symbol_map:
            out = re.sub(pat, repl, out)

        def _replace_int_hi(m: re.Match) -> str:
            return hindi_number_to_words(int(m.group(0)))

        out = re.sub(r"\b\d+\b", _replace_int_hi, out)

    elif lang in ("ta", "tam_Taml"):
        symbol_map = [
            (r"\b(\d+)\s*(?:Ω|Ohms?|ஓம்)\b", r"\1 ஓம்"),
            (r"\b(\d+)\s*(?:V|Volts?|வோல்ட்)\b", r"\1 வோல்ட்"),
            (r"\b(\d+)\s*(?:A|Amperes?|ஆம்பியர்)\b", r"\1 ஆம்பியர்"),
            (r"\b(\d+)\s*(?:W|Watts?|வாட்)\b", r"\1 வாட்"),
            (r"\b(\d+)\s*(?:Hz|Hertz|ஹெர்ட்ஸ்)\b", r"\1 ஹெர்ட்ஸ்"),
            (r"\b(\d+)\s*%", r"\1 சதவீதம்"),
            (r"\b(\d+)\s*fps\b", r"\1 பிரேம் பர் வினாடி"),
            (r"\b(\d+)\s*(?:s|sec|வினாடி)\b", r"\1 வினாடி"),
            (r"\s*=\s*", " சமம் "),
            (r"\s*(?:×|\*)\s*", " பெருக்கல் "),
            (r"\s*(?:÷|\/)\s*", " வகுத்தல் "),
            (r"\s*\+\s*", " கூட்டல் "),
            (r"\s*-\s*", " கழித்தல் "),
            (r"\s*→\s*", " வழிவகுக்கிறது "),
        ]
        for pat, repl in symbol_map:
            out = re.sub(pat, repl, out)

        def _replace_int_ta(m: re.Match) -> str:
            return tamil_number_to_words(int(m.group(0)))

        out = re.sub(r"\b\d+\b", _replace_int_ta, out)

    elif lang in ("bn", "ben_Beng"):
        symbol_map = [
            (r"\b(\d+)\s*(?:Ω|Ohms?|ওহম)\b", r"\1 ওহম"),
            (r"\b(\d+)\s*(?:V|Volts?|ভোল্ট)\b", r"\1 ভোল্ট"),
            (r"\b(\d+)\s*(?:A|Amperes?|অ্যাম্পিয়ার)\b", r"\1 অ্যাম্পিয়ার"),
            (r"\b(\d+)\s*(?:W|Watts?|ওয়াট)\b", r"\1 ওয়াট"),
            (r"\b(\d+)\s*(?:Hz|Hertz|হার্টজ)\b", r"\1 হার্টজ"),
            (r"\b(\d+)\s*%", r"\1 শতাংশ"),
            (r"\b(\d+)\s*fps\b", r"\1 ফ্রেম প্রতি সেকেন্ড"),
            (r"\b(\d+)\s*(?:s|sec|সেকেন্ড)\b", r"\1 সেকেন্ড"),
            (r"\s*=\s*", " সমান "),
            (r"\s*(?:×|\*)\s*", " গুণ "),
            (r"\s*(?:÷|\/)\s*", " ভাগ "),
            (r"\s*\+\s*", " প্লাস "),
            (r"\s*-\s*", " মাইনাস "),
            (r"\s*→\s*", " বোঝায় "),
        ]
        for pat, repl in symbol_map:
            out = re.sub(pat, repl, out)

        def _replace_int_bn(m: re.Match) -> str:
            return bengali_number_to_words(int(m.group(0)))

        out = re.sub(r"\b\d+\b", _replace_int_bn, out)

    else:
        symbol_map = [
            (r"\b(\d+)\s*(?:Ω|Ohms?)\b", r"\1 ohms"),
            (r"\b(\d+)\s*(?:V|Volts?)\b", r"\1 volts"),
            (r"\b(\d+)\s*(?:A|Amperes?)\b", r"\1 amperes"),
            (r"\b(\d+)\s*(?:W|Watts?)\b", r"\1 watts"),
            (r"\b(\d+)\s*(?:Hz|Hertz)\b", r"\1 hertz"),
            (r"\b(\d+)\s*%", r"\1 percent"),
            (r"\s*=\s*", " equals "),
            (r"\s*(?:×|\*)\s*", " times "),
            (r"\s*(?:÷|\/)\s*", " divided by "),
            (r"\s*\+\s*", " plus "),
            (r"\s*-\s*", " minus "),
            (r"\s*→\s*", " leads to "),
        ]
        for pat, repl in symbol_map:
            out = re.sub(pat, repl, out)

        def _replace_int_en(m: re.Match) -> str:
            return english_number_to_words(int(m.group(0)))

        out = re.sub(r"\b\d+\b", _replace_int_en, out)

    # Collapse extra whitespace
    return re.sub(r"\s+", " ", out).strip()


# ---------------------------------------------------------------------------
# Offline TTS Engine
# ---------------------------------------------------------------------------
def _has_espeakng_loader() -> bool:
    try:
        import espeakng_loader
        return Path(espeakng_loader.get_library_path()).exists()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Audio Time Scaling (Expansion & Compression)
# ---------------------------------------------------------------------------
def time_scale_audio(
    wav: Any,
    target_samples: int,
    sr: int = TARGET_SR,
    tail_pad_samples: int = 8400,
) -> Any:
    """Scale audio waveform to exact target_samples using expansion or compression.
    
    Preserves 0.35s tail silence padding so speech does not clip before scene cuts.
    Works seamlessly across NumPy arrays and pure Python lists of floats.
    """
    total_len = len(wav)
    if total_len == target_samples:
        return wav

    # Extract speech portion and tail pad
    if total_len > tail_pad_samples:
        speech = wav[:-tail_pad_samples]
    else:
        speech = wav
        tail_pad_samples = 0

    target_speech_samples = target_samples - tail_pad_samples
    if target_speech_samples <= 0:
        target_speech_samples = target_samples
        tail_pad_samples = 0

    speech_len = len(speech)
    if speech_len == 0:
        if HAS_NUMPY and isinstance(wav, np.ndarray):
            return np.zeros(target_samples, dtype=np.float32)
        return [0.0] * target_samples

    if HAS_NUMPY and isinstance(wav, np.ndarray):
        # High performance NumPy linear interpolation resampling
        old_indices = np.linspace(0, speech_len - 1, target_speech_samples)
        scaled_speech = np.interp(old_indices, np.arange(speech_len), speech).astype(np.float32)
        pad = np.zeros(tail_pad_samples, dtype=np.float32)
        return np.concatenate([scaled_speech, pad])
    else:
        # Pure Python linear interpolation fallback
        scaled_speech = []
        step = (speech_len - 1) / max(1, target_speech_samples - 1) if target_speech_samples > 1 else 0.0
        for i in range(target_speech_samples):
            pos = i * step
            idx = int(pos)
            frac = pos - idx
            s0 = speech[idx]
            s1 = speech[idx + 1] if idx + 1 < speech_len else s0
            scaled_speech.append(s0 * (1.0 - frac) + s1 * frac)
        return scaled_speech + [0.0] * tail_pad_samples


class OfflineTTSEngine:
    """Dual-engine TTS generating synchronized scene audio and timing manifests.
    
    Uses Kokoro-82M for English/Hindi and MMS-TTS for Kannada/Indic.
    Standardizes all output to 24 kHz mono with 0.35s tail padding per scene.
    """

    def __init__(self):
        self.device = "cuda" if (HAS_TORCH and torch.cuda.is_available()) else "cpu"
        self.kokoro_en = None
        self.kokoro_hi = None
        self.mms_models: dict[str, Any] = {}
        self.mms_tokenizers: dict[str, Any] = {}
        self.has_espeak = bool(shutil.which("espeak-ng") or shutil.which("espeak") or _has_espeakng_loader())

        # Preload Kokoro pipelines if available
        if HAS_KOKORO:
            try:
                self.kokoro_en = KPipeline(lang_code="a")
            except Exception:
                self.kokoro_en = None

            # Hindi Kokoro requires espeak-ng; guard to prevent crash on Windows
            if self.has_espeak:
                try:
                    self.kokoro_hi = KPipeline(lang_code="h")
                except Exception:
                    self.kokoro_hi = None
            else:
                self.kokoro_hi = None

        # Preload MMS-TTS checkpoints for Kannada and bonus Indic languages
        if HAS_TORCH:
            for code, repo in [
                ("kn", "facebook/mms-tts-kan"),
                ("hi", "facebook/mms-tts-hin"),
                ("ta", "facebook/mms-tts-tam"),
                ("bn", "facebook/mms-tts-ben"),
            ]:
                try:
                    self.mms_tokenizers[code] = AutoTokenizer.from_pretrained(
                        repo, local_files_only=True
                    )
                    self.mms_models[code] = (
                        VitsModel.from_pretrained(repo, local_files_only=True)
                        .to(self.device)
                        .eval()
                    )
                except Exception:
                    pass

    def _synthesize_synthetic(self, text: str, lang: str, target_dur: float | None = None) -> tuple[Any, float]:
        """Synthetic fallback generating accurate duration audio when neural models are absent."""
        if target_dur is not None and target_dur > 0:
            total_dur = round(target_dur, 3)
            pad_samples = int(round(TAIL_PAD_SEC * TARGET_SR))
            total_samples = int(round(total_dur * TARGET_SR))
            n_samples = max(0, total_samples - pad_samples)
            dur = max(0.1, n_samples / TARGET_SR)
        else:
            words = text.split()
            dur = round(max(2.0, len(words) / WORDS_PER_SEC), 3)
            n_samples = int(round(dur * TARGET_SR))
            pad_samples = int(round(TAIL_PAD_SEC * TARGET_SR))
            total_samples = n_samples + pad_samples
            total_dur = round(total_samples / TARGET_SR, 3)

        if HAS_NUMPY:
            t = np.linspace(0, dur, n_samples, endpoint=False)
            freq = 440.0 if lang == "en" else (554.37 if lang == "hi" else 659.25)
            # Gentle bell envelope for pleasant synthetic tone
            env = np.sin(np.pi * np.linspace(0, 1, n_samples))
            audio = (0.90 * env * np.sin(2 * np.pi * freq * t)).astype(np.float32)
            pad = np.zeros(pad_samples, dtype=np.float32)
            wav = np.concatenate([audio, pad])
        else:
            freq = 440.0 if lang == "en" else (554.37 if lang == "hi" else 659.25)
            audio = [
                0.90 * math.sin(math.pi * i / n_samples) * math.sin(2 * math.pi * freq * i / TARGET_SR)
                for i in range(n_samples)
            ]
            pad = [0.0] * pad_samples
            wav = audio + pad

        total_dur = round(total_samples / TARGET_SR, 3)
        return wav, total_dur

    def synthesize_scene(self, text: str, lang: str, target_dur: float | None = None) -> tuple[Any, float]:
        """Synthesize scene audio waveform with numbers expanded and tail pad attached.
        
        Returns:
            (waveform_array, measured_duration_sec)
            Note: measured_duration_sec INCLUDES the 0.35s tail pad.
        """
        # Step 1: Preprocess text (expand numbers & math symbols)
        clean_text = expand_numbers_and_symbols(text, lang)

        # Step 2: Try neural synthesis
        pad_samples = int(TAIL_PAD_SEC * TARGET_SR)

        if lang == "en" and self.kokoro_en is not None and HAS_NUMPY:
            try:
                chunks = [
                    audio
                    for _, _, audio in self.kokoro_en(clean_text, voice="af_heart", speed=1.0)
                    if audio is not None
                ]
                if chunks:
                    speech_wav = np.concatenate(chunks).astype(np.float32)
                    pad = np.zeros(pad_samples, dtype=np.float32)
                    full_wav = np.concatenate([speech_wav, pad])
                    if target_dur is not None and target_dur > 0:
                        target_samples = int(round(target_dur * TARGET_SR))
                        full_wav = time_scale_audio(full_wav, target_samples, sr=TARGET_SR, tail_pad_samples=pad_samples)
                    measured_dur = round(len(full_wav) / TARGET_SR, 3)
                    return full_wav, measured_dur
            except Exception:
                pass

        if lang == "hi" and self.kokoro_hi is not None and HAS_NUMPY:
            try:
                chunks = [
                    audio
                    for _, _, audio in self.kokoro_hi(clean_text, voice="hf_alpha", speed=1.0)
                    if audio is not None
                ]
                if chunks:
                    speech_wav = np.concatenate(chunks).astype(np.float32)
                    pad = np.zeros(pad_samples, dtype=np.float32)
                    full_wav = np.concatenate([speech_wav, pad])
                    if target_dur is not None and target_dur > 0:
                        target_samples = int(round(target_dur * TARGET_SR))
                        full_wav = time_scale_audio(full_wav, target_samples, sr=TARGET_SR, tail_pad_samples=pad_samples)
                    measured_dur = round(len(full_wav) / TARGET_SR, 3)
                    return full_wav, measured_dur
            except Exception:
                pass

        # MMS-TTS path (Kannada, or Hindi fallback if espeak is missing)
        mms_lang = lang if lang in self.mms_models else ("hi" if lang == "hi" else None)
        if mms_lang and mms_lang in self.mms_models and HAS_TORCH and HAS_NUMPY:
            try:
                # Call clean_for_mms before every MMS-TTS call
                mms_input_text = clean_for_mms(clean_text, mms_lang)
                tokenizer = self.mms_tokenizers[mms_lang]
                model = self.mms_models[mms_lang]
                inputs = tokenizer(mms_input_text, return_tensors="pt").to(self.device)

                # Deterministic duration predictor fix (crucial for zero drift)
                torch.manual_seed(42)
                with torch.no_grad():
                    out = model(**inputs).waveform.squeeze().cpu().numpy()

                # Resample 16,000 Hz -> 24,000 Hz (3:2 ratio)
                if HAS_SCIPY:
                    speech_wav = resample_poly(out, up=3, down=2).astype(np.float32)
                else:
                    # Linear interpolation fallback
                    old_len = len(out)
                    new_len = int(old_len * 1.5)
                    speech_wav = np.interp(
                        np.linspace(0, old_len, new_len), np.arange(old_len), out
                    ).astype(np.float32)

                pad = np.zeros(pad_samples, dtype=np.float32)
                full_wav = np.concatenate([speech_wav, pad])
                if target_dur is not None and target_dur > 0:
                    target_samples = int(round(target_dur * TARGET_SR))
                    full_wav = time_scale_audio(full_wav, target_samples, sr=TARGET_SR, tail_pad_samples=pad_samples)
                measured_dur = round(len(full_wav) / TARGET_SR, 3)
                return full_wav, measured_dur
            except Exception:
                pass

        # Step 3: Fallback synthesis
        return self._synthesize_synthetic(clean_text, lang, target_dur=target_dur)

    def synthesize_all_scenes(
        self,
        scenes: Sequence[Any],
        lang: str,
        out_wav_path: str | Path,
        target_durations: Sequence[float] | Sequence[dict] | None = None,
    ) -> list[dict]:
        """Synthesize audio for all scenes and output timing manifest and master WAV.
        
        Zero Double-Padding Enforcement:
          - Each scene audio includes the 0.35s tail pad.
          - Scene duration in timing_manifest equals the exact length of that audio.
          - start_sec and end_sec are strictly cumulative.
        """
        out_wav_path = Path(out_wav_path)
        out_wav_path.parent.mkdir(parents=True, exist_ok=True)

        timing_manifest: list[dict] = []
        cursor_sec = 0.0
        all_waveforms = []

        for idx, s in enumerate(scenes):
            text = getattr(s, "narration", None) or (s.get("narration") if isinstance(s, dict) else s["narration"])
            sid = getattr(s, "id", None) or (s.get("id") if isinstance(s, dict) else s["id"])
            vis = getattr(s, "visual", None) if hasattr(s, "visual") else (s.get("visual") if isinstance(s, dict) else s["visual"])
            visual = vis.model_dump() if hasattr(vis, "model_dump") else (vis if isinstance(vis, dict) else dict(vis))

            target_dur = None
            if target_durations is not None and idx < len(target_durations):
                item = target_durations[idx]
                target_dur = float(item["duration_sec"]) if isinstance(item, dict) else float(item)

            wav, duration_sec = self.synthesize_scene(text, lang, target_dur=target_dur)
            all_waveforms.append(wav)

            timing_manifest.append({
                "id": sid,
                "start_sec": round(cursor_sec, 3),
                "end_sec": round(cursor_sec + duration_sec, 3),
                "duration_sec": round(duration_sec, 3),
                "narration": text,
                "visual": visual,
            })
            cursor_sec += duration_sec

        # Concatenate and write master WAV
        self._write_master_wav(all_waveforms, out_wav_path)

        return timing_manifest

    def synthesize_multilingual_all_scenes(
        self,
        plans: dict[str, Any],
        out_base_dir: str | Path,
        reference_lang: str = "en",
    ) -> dict[str, list[dict]]:
        """Synthesize all scenes across multiple localized plans with synchronized timing.
        
        The reference_lang (default 'en') establishes the master timing manifest.
        All other languages apply audio time expansion and compression to match
        the exact scene durations and total length of the reference language.
        """
        out_base_dir = Path(out_base_dir)
        manifests: dict[str, list[dict]] = {}

        # 1. Synthesize reference language first to establish master timing
        ref_plan = plans[reference_lang]
        ref_scenes = getattr(ref_plan, "scenes", ref_plan)
        ref_dir = out_base_dir / f"{reference_lang}"
        ref_dir.mkdir(parents=True, exist_ok=True)
        ref_wav = ref_dir / "lesson_audio.wav"
        ref_manifest = self.synthesize_all_scenes(ref_scenes, reference_lang, ref_wav)
        manifests[reference_lang] = ref_manifest
        target_durations = [s["duration_sec"] for s in ref_manifest]

        # 2. Synthesize other languages synchronized to reference scene durations
        for lang, plan in plans.items():
            if lang == reference_lang:
                continue
            scenes = getattr(plan, "scenes", plan)
            lang_dir = out_base_dir / f"{lang}"
            lang_dir.mkdir(parents=True, exist_ok=True)
            lang_wav = lang_dir / "lesson_audio.wav"
            manifests[lang] = self.synthesize_all_scenes(
                scenes, lang, lang_wav, target_durations=target_durations
            )

        return manifests

    def _write_master_wav(self, waveforms: list[Any], out_path: Path) -> None:
        """Write 24,000 Hz, 16-bit mono master WAV with peak normalization."""
        if HAS_NUMPY and waveforms and isinstance(waveforms[0], np.ndarray):
            master = np.concatenate(waveforms)
            # Peak normalize to -1 dBFS (0.89 amplitude)
            peak = float(np.max(np.abs(master)))
            if peak > 0:
                master = master * (0.90 / peak)
            int16_data = (master * 32767).astype(np.int16).tobytes()
        else:
            # Fallback packing with 0.90 peak normalization
            frames = []
            max_val = 0.0
            for w in waveforms:
                if isinstance(w, (list, tuple)):
                    for s in w:
                        if abs(s) > max_val:
                            max_val = abs(s)
            scale = (0.90 / max_val) if max_val > 1e-4 else 1.0
            for w in waveforms:
                if isinstance(w, (list, tuple)):
                    for sample in w:
                        val = int(max(-1.0, min(1.0, sample * scale)) * 32767)
                        frames.append(struct.pack("<h", val))
            int16_data = b"".join(frames) if frames else b"\x00\x00" * int(TARGET_SR * 2)

        with wave.open(str(out_path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(TARGET_SR)
            w.writeframes(int16_data)


# ---------------------------------------------------------------------------
# Manifest Builder
# ---------------------------------------------------------------------------
def build_manifest(
    plan: Any,
    timing_manifest: list[dict],
    lang: str,
    audio_filename: str = "lesson_audio.wav",
    sample_rate: int = TARGET_SR,
) -> dict:
    """Build the final manifest dictionary conforming to PLAN.md 4.3."""
    total_sec = timing_manifest[-1]["end_sec"] if timing_manifest else 0.0
    title = plan.title if hasattr(plan, "title") else plan.get("title", "")
    return {
        "title": title,
        "lang": lang,
        "total_sec": total_sec,
        "audio": audio_filename,
        "sample_rate": sample_rate,
        "scenes": timing_manifest,
    }
