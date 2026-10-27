"""tests/test_natural_prosody_and_translation.py — Comprehensive verification of natural speech and translation enhancements.

Verifies:
  1. STEM acronym verbalization across all 5 languages (LED, AC, DC, DNA, CPU, RAM, etc.).
  2. Natural clause-boundary breath pause insertion (insert_breath_pauses) for human-like Indic prosody.
  3. Pre-TTS cleaning (clean_for_mms) guarantees 0 ASCII digits, expanded acronyms, and natural pause commas.
  4. Soft attack/release audio envelope eliminates audio pops/clicks at scene boundaries.
  5. Multi-model voice selection and calm educational pace parameters in OfflineTTSEngine.
  6. Bengali support in translator: LANG_CODE_MAP, ensure_word_budget, Devanagari leakage sanitization.
  7. Advanced STEM formula and scientific notation protection in PROTECT.
  8. Time scaling with soft envelope preserves sample-exact synchronization and silent tail buffer.
"""

from __future__ import annotations

import math
from pathlib import Path
import pytest

from localization.normalize import (
    STEM_ACRONYMS,
    clean_for_mms,
    count_ascii_digits,
    expand_numbers_and_symbols,
    expand_stem_acronyms,
    insert_breath_pauses,
)
from localization.translator import (
    LANG_CODE_MAP,
    PROTECT,
    ensure_word_budget,
    extract_protected_spans,
    mask_protected_spans,
    restore_protected_spans,
    sanitize_kannada_output,
    contains_devanagari,
    verify_spans_survived,
)
from localization.tts_engine import (
    OfflineTTSEngine,
    TARGET_SR,
    TAIL_PAD_SEC,
    apply_soft_envelope,
    time_scale_audio,
)


# ---------------------------------------------------------------------------
# 1. STEM Acronym Verbalization Tests
# ---------------------------------------------------------------------------
def test_expand_stem_acronyms_across_languages():
    """Verify STEM acronyms expand to native phonetic words in all 5 languages."""
    test_text = "The LED bulb connects to an AC circuit with a CPU and RAM chip."

    # English
    en_exp = expand_stem_acronyms("LED AC DC CPU RAM", "en")
    assert "L E D" in en_exp
    assert "A C" in en_exp
    assert "D C" in en_exp
    assert "C P U" in en_exp

    # Hindi
    hi_exp = expand_stem_acronyms("LED AC DC DNA CPU RAM", "hi")
    assert "एलईडी" in hi_exp
    assert "एसी" in hi_exp
    assert "डीसी" in hi_exp
    assert "डीएनए" in hi_exp
    assert "सीपीयू" in hi_exp
    assert "रैम" in hi_exp

    # Kannada
    kn_exp = expand_stem_acronyms("LED AC DC DNA CPU RAM", "kn")
    assert "ಎಲ್ಇಡಿ" in kn_exp
    assert "ಎಸಿ" in kn_exp
    assert "ಡಿಸಿ" in kn_exp
    assert "ಡಿಎನ್‌ಎ" in kn_exp
    assert "ಸಿಪಿಯು" in kn_exp
    assert "ರ್ಯಾಮ್" in kn_exp

    # Tamil
    ta_exp = expand_stem_acronyms("LED AC DC DNA CPU RAM", "ta")
    assert "எல்இடி" in ta_exp
    assert "ஏசி" in ta_exp
    assert "டிசி" in ta_exp
    assert "டிஎன்ஏ" in ta_exp
    assert "சிபியு" in ta_exp
    assert "ரேம்" in ta_exp

    # Bengali
    bn_exp = expand_stem_acronyms("LED AC DC DNA CPU RAM", "bn")
    assert "এলইডি" in bn_exp
    assert "এসি" in bn_exp
    assert "ডিসি" in bn_exp
    assert "ডিএনএ" in bn_exp
    assert "সিপিইউ" in bn_exp
    assert "র‌্যাম" in bn_exp


# ---------------------------------------------------------------------------
# 2. Natural Clause-Boundary Breath Pauses
# ---------------------------------------------------------------------------
def test_insert_breath_pauses_indic():
    """Verify natural micro-pauses (commas) are added after conjunctions without punctuation."""
    # Hindi
    hi_raw = "वोल्टेज बढ़ता है लेकिन धारा स्थिर रहती है क्योंकि प्रतिरोध अधिक है"
    hi_paused = insert_breath_pauses(hi_raw, "hi")
    assert "लेकिन," in hi_paused
    assert "क्योंकि," in hi_paused

    # Kannada
    kn_raw = "ವೋಲ್ಟೇಜ್ ಹೆಚ್ಚಾಗುತ್ತದೆ ಆದರೆ ಕರೆಂಟ್ ಸ್ಥಿರವಾಗಿರುತ್ತದೆ ಏಕೆಂದರೆ ರೋಧವಿದೆ"
    kn_paused = insert_breath_pauses(kn_raw, "kn")
    assert "ಆದರೆ," in kn_paused
    assert "ಏಕೆಂದರೆ," in kn_paused

    # Tamil
    ta_raw = "மின்னழுத்தம் அதிகரிக்கிறது ஆனால் மின்னோட்டம் நிலையானது ஏனெனில் மின்தடை உள்ளது"
    ta_paused = insert_breath_pauses(ta_raw, "ta")
    assert "ஆனால்," in ta_paused
    assert "ஏனெனில்," in ta_paused

    # Bengali
    bn_raw = "ভোল্টেজ বৃদ্ধি পায় কিন্তু কারেন্ট অপরিবর্তিত থাকে কারণ রোধ বেশি"
    bn_paused = insert_breath_pauses(bn_raw, "bn")
    assert "কিন্তু," in bn_paused
    assert "কারণ," in bn_paused

    # Do not duplicate commas if already present
    already_paused = "ভোল্টেজ বৃদ্ধি পায় কিন্তু, কারেন্ট অপরিবর্তিত থাকে"
    assert insert_breath_pauses(already_paused, "bn") == already_paused


# ---------------------------------------------------------------------------
# 3. Clean for MMS Pre-TTS Sanitation
# ---------------------------------------------------------------------------
def test_clean_for_mms_with_acronyms_and_pauses():
    """Verify clean_for_mms expands STEM acronyms, strips digits, and formats breath pauses."""
    text_kn = "LED ದೀಪವು 230 V ಗೆ ಸಂಪರ್ಕಗೊಂಡಿದೆ ಆದರೆ ಕರೆಂಟ್ ಕಡಿಮೆಯಾಗಿದೆ"
    clean_kn = clean_for_mms(text_kn, "kn")

    # LED expanded
    assert "ಎಲ್ಇಡಿ" in clean_kn
    assert "LED" not in clean_kn

    # 230 V expanded
    assert "ಇನ್ನೂರ ಮೂವತ್ತು ವೋಲ್ಟ್" in clean_kn
    assert count_ascii_digits(clean_kn) == 0

    # Breath pause added after ಆದರೆ
    assert "ಆದರೆ," in clean_kn


# ---------------------------------------------------------------------------
# 4. Soft Attack & Release Audio Envelope (Anti-Pop)
# ---------------------------------------------------------------------------
def test_apply_soft_envelope_smoothness():
    """Verify soft envelope ramps audio from zero and decays to zero smoothly."""
    sr = TARGET_SR
    # Create 0.5s constant square waveform of amplitude 1.0
    n_samples = int(0.5 * sr)
    raw_audio = [1.0] * n_samples

    enveloped = apply_soft_envelope(raw_audio, sr=sr, attack_ms=5.0, release_ms=10.0)
    assert len(enveloped) == n_samples

    # First sample must start at zero (anti-pop attack)
    assert abs(enveloped[0]) < 1e-5

    # Last sample must end at zero (anti-pop release)
    assert abs(enveloped[-1]) < 1e-5

    # Middle sample must retain full amplitude
    mid = n_samples // 2
    assert abs(enveloped[mid] - 1.0) < 1e-4

    # Monotonic ramp up in attack region
    attack_samples = int(round(5.0 * sr / 1000.0))
    for i in range(1, attack_samples):
        assert enveloped[i] >= enveloped[i - 1] - 1e-6


# ---------------------------------------------------------------------------
# 5. Time Scaling with Soft Envelope
# ---------------------------------------------------------------------------
def test_time_scale_audio_envelope_and_silence():
    """Verify time scaling scales speech smoothly and preserves pure zero tail padding."""
    sr = TARGET_SR
    pad_samples = int(TAIL_PAD_SEC * sr)
    total_samples = int(4.0 * sr)
    speech_samples = total_samples - pad_samples

    sine_speech = [0.8 * math.sin(2 * math.pi * 440 * i / sr) for i in range(speech_samples)]
    wav = sine_speech + [0.0] * pad_samples

    target_samples = int(5.5 * sr)
    scaled = time_scale_audio(wav, target_samples, sr=sr, tail_pad_samples=pad_samples)

    assert len(scaled) == target_samples

    # Check tail pad is absolute zero
    tail = scaled[-pad_samples:]
    assert all(abs(s) < 1e-6 for s in tail)

    # Check boundary before tail is smoothed
    scaled_speech = scaled[:-pad_samples]
    assert abs(scaled_speech[-1]) < 0.05


# ---------------------------------------------------------------------------
# 6. Multi-Model Voice & Cadence Configuration
# ---------------------------------------------------------------------------
def test_tts_engine_custom_voice_and_cadence():
    """Verify OfflineTTSEngine initializes with custom voices and human educational pace."""
    tts = OfflineTTSEngine(
        voice_en="af_heart",
        speed_en=0.98,
        voice_hi="hf_alpha",
        speed_hi=0.98,
        mms_speaking_rate=0.95,
    )
    assert tts.voice_en == "af_heart"
    assert tts.speed_en == 0.98
    assert tts.voice_hi == "hf_alpha"
    assert tts.speed_hi == 0.98
    assert tts.mms_speaking_rate == 0.95


# ---------------------------------------------------------------------------
# 7. Bengali Translation & Discourse Markers
# ---------------------------------------------------------------------------
def test_bengali_language_integration():
    """Verify Bengali is fully integrated into LANG_CODE_MAP, discourse markers, and script rules."""
    assert "bn" in LANG_CODE_MAP
    assert LANG_CODE_MAP["bn"] == "ben_Beng"

    # Short sentence expands with natural classroom prefix to >= 8 words
    short_bn = "ভোল্টেজ এবং কারেন্ট।"
    expanded = ensure_word_budget(short_bn, "bn", min_words=8, max_words=42)
    words = expanded.split()
    assert len(words) >= 8
    assert "ভোল্টেজ" in expanded

    # Devanagari leakage sanitization in Bengali
    leak_sample = "ভোল্টেজ वोल्टेज কারেন্ট"
    sanitized = sanitize_kannada_output(leak_sample)
    assert not contains_devanagari(sanitized)
    assert "ভোল্টেজ" in sanitized
    assert "কারেন্ট" in sanitized


# ---------------------------------------------------------------------------
# 8. Advanced STEM Formula Protection in Translator
# ---------------------------------------------------------------------------
def test_protect_advanced_stem_formulas():
    """Verify PROTECT list shields advanced formulas, powers, scientific notations, and chemistry."""
    test_cases = [
        ("Power dissipated is P = V^2 / R in the circuit.", ["P = V^2 / R"]),
        ("Speed of light in vacuum is 3 × 10^8 m/s.", ["3 × 10^8 m/s"]),
        ("Water formula is H2O and carbon dioxide is CO2.", ["H2O", "CO2"]),
        ("Input voltage V_in = 230 V provides electrical energy.", ["V_in = 230 V"]),
        ("Kinematic relation: v^2 = u^2 + 2as.", ["v^2 = u^2 + 2as"]),
    ]

    for sentence, expected_spans in test_cases:
        spans = extract_protected_spans(sentence, PROTECT)
        extracted_texts = [s[2] for s in spans]
        for exp in expected_spans:
            assert any(exp in ext for ext in extracted_texts), f"Expected '{exp}' to be protected in '{sentence}', got {extracted_texts}"

        # Mask and restore
        masked, prot = mask_protected_spans(sentence, spans)
        restored = restore_protected_spans(masked, prot)
        assert restored == sentence
        assert verify_spans_survived(restored, prot)
