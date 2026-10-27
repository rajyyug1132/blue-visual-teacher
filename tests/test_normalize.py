"""tests/test_normalize.py — Verification of speak_en(), fix_residual_digits(), and clean_for_mms().

Evaluates the test cases:
  - "230 V"
  - "46 Ω"
  - "100 °C"
  - "6.5%"
  - "2023"
  - "H = 2"

Verifies:
  1. speak_en() normalizes English units, temperatures, percentages, and math symbols.
  2. fix_residual_digits() converts residual ASCII digits into Hindi/Kannada native script words.
  3. clean_for_mms() strips and normalizes text for Meta MMS-TTS, guaranteeing 0 ASCII digits remain.
  4. Prints results for hi and kn and reports any ASCII digits left.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from localization.normalize import (
    clean_for_mms,
    count_ascii_digits,
    english_number_to_words,
    fix_residual_digits,
    has_ascii_digits,
    hindi_number_to_words,
    kannada_number_to_words,
    tamil_number_to_words,
    telugu_number_to_words,
    speak_en,
)

TEST_CASES: list[str] = [
    "230 V",
    "46 Ω",
    "100 °C",
    "6.5%",
    "2023",
    "H = 2",
]

# Realistic post-IndicTrans2 translations where residual digits or symbols remain
SIMULATED_TRANSLATIONS: dict[str, dict[str, str]] = {
    "230 V": {
        "hi": "230 वोल्ट",
        "kn": "230 ವೋಲ್ಟ್",
        "ta": "230 வோல்ட்",
        "te": "230 వోల్ట్",
    },
    "46 Ω": {
        "hi": "46 ओम",
        "kn": "46 ಓಮ್",
        "ta": "46 ஓம்",
        "te": "46 ఓమ్",
    },
    "100 °C": {
        "hi": "100 डिग्री सेल्सियस",
        "kn": "100 ಡಿಗ್ರಿ ಸೆಲ್ಸಿಯಸ್",
        "ta": "100 டிகிரி செல்சியஸ்",
        "te": "100 డిగ్రీ సెల్సియస్",
    },
    "6.5%": {
        "hi": "6.5 प्रतिशत",
        "kn": "6.5 ಪ್ರತಿಶತ",
        "ta": "6.5 சதவீதம்",
        "te": "6.5 శాతం",
    },
    "2023": {
        "hi": "2023",
        "kn": "2023",
        "ta": "2023",
        "te": "2023",
    },
    "H = 2": {
        "hi": "H बराबर 2",
        "kn": "H ಸಮಾನ 2",
        "ta": "H சமம் 2",
        "te": "H సమానం 2",
    },
}


def test_speak_en_expansions():
    """Verify speak_en correctly expands English units, temperatures, percentages, and symbols."""
    assert speak_en("230 V") == "230 volts"
    assert speak_en("46 Ω") == "46 ohms"
    assert speak_en("100 °C") == "100 degrees Celsius"
    assert speak_en("6.5%") == "6.5 percent"
    assert speak_en("2023") == "2023"
    assert speak_en("H = 2") == "H equals 2"


def test_fix_residual_digits_hi():
    """Verify Hindi residual digit expansion produces zero ASCII digits."""
    for case in TEST_CASES:
        trans_hi = SIMULATED_TRANSLATIONS[case]["hi"]
        res = fix_residual_digits(trans_hi, "hi")
        assert not has_ascii_digits(res), f"Residual digits found in hi: '{res}'"
        assert count_ascii_digits(res) == 0


def test_fix_residual_digits_kn():
    """Verify Kannada residual digit expansion produces zero ASCII digits."""
    for case in TEST_CASES:
        trans_kn = SIMULATED_TRANSLATIONS[case]["kn"]
        res = fix_residual_digits(trans_kn, "kn")
        assert not has_ascii_digits(res), f"Residual digits found in kn: '{res}'"
        assert count_ascii_digits(res) == 0


def test_fix_residual_digits_ta():
    """Verify Tamil residual digit expansion produces zero ASCII digits."""
    for case in TEST_CASES:
        trans_ta = SIMULATED_TRANSLATIONS[case]["ta"]
        res = fix_residual_digits(trans_ta, "ta")
        assert not has_ascii_digits(res), f"Residual digits found in ta: '{res}'"
        assert count_ascii_digits(res) == 0


def test_fix_residual_digits_te():
    """Verify Telugu residual digit expansion produces zero ASCII digits."""
    for case in TEST_CASES:
        trans_te = SIMULATED_TRANSLATIONS[case]["te"]
        res = fix_residual_digits(trans_te, "te")
        assert not has_ascii_digits(res), f"Residual digits found in te: '{res}'"
        assert count_ascii_digits(res) == 0


def test_clean_for_mms_guarantees_zero_ascii_digits():
    """Verify clean_for_mms removes all ASCII digits and math symbols for MMS-TTS."""
    for case in TEST_CASES:
        for lang in ("hi", "kn", "ta", "te"):
            # Direct raw case
            res_raw = clean_for_mms(case, lang)
            assert not has_ascii_digits(res_raw), f"Direct raw clean_for_mms failed for {case} ({lang}): '{res_raw}'"

            # Post-translation case
            trans = SIMULATED_TRANSLATIONS[case][lang]
            res_trans = clean_for_mms(trans, lang)
            assert not has_ascii_digits(res_trans), f"Translated clean_for_mms failed for {case} ({lang}): '{res_trans}'"


def run_benchmark_and_print():
    """Run all normalization stages across test cases and print detailed results table."""
    print("\n" + "=" * 96)
    print("NORMALIZATION & RESIDUAL DIGIT BENCHMARK (hi, kn, ta, te)")
    print("=" * 96)
    header = f"{'Case':<10} {'speak_en()':<24} {'Lang':<6} {'Post-Trans + clean_for_mms()':<36} {'ASCII Digits Left':<18}"
    print(header)
    print("-" * 96)

    total_digits_left = 0
    results_summary = []

    for case in TEST_CASES:
        sp = speak_en(case)
        for lang in ("hi", "kn", "ta", "te"):
            trans = SIMULATED_TRANSLATIONS[case][lang]
            cleaned = clean_for_mms(trans, lang)
            digits_left = count_ascii_digits(cleaned)
            total_digits_left += digits_left
            status = "0 (PASS)" if digits_left == 0 else f"{digits_left} (FAIL)"

            row = f"{case:<10} {sp:<24} {lang:<6} {cleaned:<36} {status:<18}"
            print(row)
            results_summary.append((case, lang, cleaned, digits_left))

    print("-" * 96)
    print(f"TOTAL ASCII DIGITS LEFT ACROSS ALL CASES: {total_digits_left}")
    print("=" * 96 + "\n")
    return total_digits_left


def test_print_and_report_results(capsys):
    """Pytest wrapper executing the benchmark and asserting zero residual ASCII digits."""
    total_left = run_benchmark_and_print()
    assert total_left == 0, f"Expected 0 ASCII digits remaining, but found {total_left}!"


if __name__ == "__main__":
    run_benchmark_and_print()
