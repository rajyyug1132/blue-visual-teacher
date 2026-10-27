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


# ---------------------------------------------------------------------------
# 9. Approach 2A (Collocation Window) + 2B (Case Enforcement) Tests
# ---------------------------------------------------------------------------
def test_stem_disambiguation_approach_2a_and_2b():
    """Verify that ambiguous STEM words (RAM, AC, DC, PI) are disambiguated via 2A & 2B."""
    # 1. RAM in hardware context -> Expanded
    t_hw1 = "The computer is equipped with 16 GB of RAM for fast processing."
    assert "ರ್ಯಾಮ್" in expand_stem_acronyms(t_hw1, "kn")
    assert "रैम" in expand_stem_acronyms(t_hw1, "hi")
    assert "ரேம்" in expand_stem_acronyms(t_hw1, "ta")
    assert "র‌্যাম" in expand_stem_acronyms(t_hw1, "bn")

    # 2. Ram in title-case but with hardware context cues -> Expanded
    t_hw2 = "The system requires 8 GB of Ram for cache memory storage."
    assert "ರ್ಯಾಮ್" in expand_stem_acronyms(t_hw2, "kn")
    assert "रैम" in expand_stem_acronyms(t_hw2, "hi")

    # 3. Ram as historical/proper noun name -> Preserved, NOT expanded
    t_hist1 = "King Ram ruled the ancient kingdom of Ayodhya with justice."
    res_hist1 = expand_stem_acronyms(t_hist1, "kn")
    assert "Ram" in res_hist1
    assert "ರ್ಯಾಮ್" not in res_hist1

    # 4. RAM in ALL-CAPS history title -> Preserved via non-STEM cues
    t_hist2 = "KING RAM OF AYODHYA WAS HONORED BY ALL CITIZENS."
    res_hist2 = expand_stem_acronyms(t_hist2, "hi")
    assert "RAM" in res_hist2
    assert "रैम" not in res_hist2

    # 5. AC in electrical circuit context -> Expanded
    t_ac_elec = "Alternating current or AC flows bidirectionally through circuits."
    assert "ಎಸಿ" in expand_stem_acronyms(t_ac_elec, "kn")
    assert "एसी" in expand_stem_acronyms(t_ac_elec, "hi")

    # 6. AC in room cooling context -> Preserved, NOT expanded as alternating current
    t_ac_cool = "Turn on the AC to cool the room during hot summer days."
    res_ac_cool = expand_stem_acronyms(t_ac_cool, "kn")
    assert "AC" in res_ac_cool
    assert "ಎಸಿ" not in res_ac_cool

    # 7. PI in math geometry context -> Expanded
    t_pi_math = "Calculate the area of the circle as pi times radius squared."
    assert "ಪೈ" in expand_stem_acronyms(t_pi_math, "kn")
    assert "पाई" in expand_stem_acronyms(t_pi_math, "hi")

    # 8. Unambiguous STEM terms expand reliably
    t_unambig = "GPU and ATP molecules assist in biological and digital systems."
    res_unambig = expand_stem_acronyms(t_unambig, "hi")
    assert "जीपीयू" in res_unambig
    assert "एटीपी" in res_unambig



# ---------------------------------------------------------------------------
# 10. Additional STEM Terms Disambiguation (Chemistry, Physics, Biology)
# ---------------------------------------------------------------------------
def test_additional_stem_disambiguation_chemistry_physics_biology():
    """Verify chemistry, physics, and biology terms (mole, base, salt, cell, mass, work, AM/FM, pH)."""
    # 1. MOLE: Chemistry vs Skin/Rodent
    t_mole_chem = "One mole of NaCl contains Avogadro number of particles in solution."
    assert "ಮೋಲ್" in expand_stem_acronyms(t_mole_chem, "kn")
    assert "मोल" in expand_stem_acronyms(t_mole_chem, "hi")
    assert "மோல்" in expand_stem_acronyms(t_mole_chem, "ta")
    assert "মোল" in expand_stem_acronyms(t_mole_chem, "bn")

    t_mole_skin = "The patient had a dark mole on his cheek."
    res_mole_skin = expand_stem_acronyms(t_mole_skin, "kn")
    assert "mole" in res_mole_skin
    assert "ಮೋಲ್" not in res_mole_skin

    # 2. BASE: Chemistry vs Military
    t_base_chem = "An acid reacts with a base to form salt and water."
    assert "ಪ್ರತ್ಯಾಮ್ಲ" in expand_stem_acronyms(t_base_chem, "kn")
    assert "क्षार" in expand_stem_acronyms(t_base_chem, "hi")

    t_base_mil = "The soldiers returned to the military base after patrol."
    res_base_mil = expand_stem_acronyms(t_base_mil, "kn")
    assert "base" in res_base_mil
    assert "ಪ್ರತ್ಯಾಮ್ಲ" not in res_base_mil

    # 3. SALT: Chemistry vs Food
    t_salt_chem = "Neutralization reaction between acid and base produces salt."
    assert "ಲವಣ" in expand_stem_acronyms(t_salt_chem, "kn")
    assert "लवण" in expand_stem_acronyms(t_salt_chem, "hi")

    t_salt_food = "Please pass the salt and pepper for the soup."
    res_salt_food = expand_stem_acronyms(t_salt_food, "kn")
    assert "salt" in res_salt_food
    assert "ಲವಣ" not in res_salt_food

    # 4. CELL: Biology vs Prison
    t_cell_bio = "Each plant cell has a nucleus and protective cell wall."
    assert "ಜೀವಕೋಶ" in expand_stem_acronyms(t_cell_bio, "kn")
    assert "कोशिका" in expand_stem_acronyms(t_cell_bio, "hi")

    t_cell_jail = "The prisoner was locked in a solitary cell."
    res_cell_jail = expand_stem_acronyms(t_cell_jail, "kn")
    assert "cell" in res_cell_jail
    assert "ಜೀವಕೋಶ" not in res_cell_jail

    # 5. MASS: Physics vs Church
    t_mass_phys = "Force equals mass times acceleration in Newton second law of motion."
    assert "ದ್ರವ್ಯರಾಶಿ" in expand_stem_acronyms(t_mass_phys, "kn")
    assert "द्रव्यमान" in expand_stem_acronyms(t_mass_phys, "hi")

    t_mass_church = "The Sunday mass at the local church started at nine."
    res_mass_church = expand_stem_acronyms(t_mass_church, "kn")
    assert "mass" in res_mass_church
    assert "ದ್ರವ್ಯರಾಶಿ" not in res_mass_church

    # 6. WORK: Physics vs Job
    t_work_phys = "In physics, work is done when force causes displacement."
    assert "ಕಾರ್ಯ" in expand_stem_acronyms(t_work_phys, "kn")
    assert "कार्य" in expand_stem_acronyms(t_work_phys, "hi")

    t_work_job = "He went to work at the corporate office today."
    res_work_job = expand_stem_acronyms(t_work_job, "kn")
    assert "work" in res_work_job

    # 7. AM and FM: Radio vs Time
    t_am_radio = "The AM radio transmitter broadcasts audio signal at 800 kHz frequency."
    assert "ಎಎಂ" in expand_stem_acronyms(t_am_radio, "kn")
    assert "एएम" in expand_stem_acronyms(t_am_radio, "hi")

    t_am_clock = "The morning flight departs at 8 AM tomorrow."
    res_am_clock = expand_stem_acronyms(t_am_clock, "kn")
    assert "AM" in res_am_clock
    assert "ಎಎಂ" not in res_am_clock

    t_fm_radio = "The FM station transmits stereo music at 98.3 MHz frequency."
    assert "ಎಫ್‌ಎಂ" in expand_stem_acronyms(t_fm_radio, "kn")
    assert "एफएम" in expand_stem_acronyms(t_fm_radio, "hi")

    # 8. Unambiguous STEM terms: pH, UV, IR, STP
    t_unambig_more = "Pure water has pH 7 at STP, while UV and IR light carry electromagnetic energy."
    res_hi = expand_stem_acronyms(t_unambig_more, "hi")
    res_kn = expand_stem_acronyms(t_unambig_more, "kn")
    assert "पीएच" in res_hi
    assert "एसटीपी" in res_hi
    assert "यूवी" in res_hi
    assert "आईआर" in res_hi
    assert "ಪಿಎಚ್" in res_kn
    assert "ಎಸ್‌ಟಿಪಿ" in res_kn
    assert "ಯುವಿ" in res_kn
    assert "ಐಆರ್" in res_kn
