"""tests/test_tts_and_localization.py — Unit tests for TTS engine, number expansion, captions, and manifest.

Verifies:
  1. Kannada number-to-words and symbol expansion (230 V -> ಇನ್ನೂರ ಮೂವತ್ತು ವೋಲ್ಟ್, 46 Ω -> ನಲವತ್ತಾರು ಓಮ್).
  2. Hindi and English number expansion.
  3. Zero double-padding: audio tail pad is included, timing_manifest duration matches measured audio directly.
  4. Kannada zero Devanagari leakage rule: no Unicode U+0900-U+097F allowed in Kannada output.
  5. Captions generator proportional word-timing.
  6. Golden manifest fixture conforms to PLAN.md 4.3 specification.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from localization.captions import compute_word_timings, generate_srt, generate_vtt
from localization.translator import (
    contains_devanagari,
    contains_kannada,
    ensure_word_budget,
    sanitize_kannada_output,
)
from localization.tts_engine import (
    TAIL_PAD_SEC,
    TARGET_SR,
    OfflineTTSEngine,
    build_manifest,
    english_number_to_words,
    expand_numbers_and_symbols,
    hindi_number_to_words,
    kannada_number_to_words,
)
from orchestrator.schema import LessonPlan

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_OHMS = ROOT / "fixtures" / "golden_ohms_law.json"
GOLDEN_MANIFEST = ROOT / "fixtures" / "golden_manifest_en.json"


# ---------------------------------------------------------------------------
# Number Expansion Tests
# ---------------------------------------------------------------------------
def test_kannada_number_to_words():
    """Verify key numbers from curriculum expand to accurate Kannada words."""
    assert kannada_number_to_words(0) == "ಸೊನ್ನೆ"
    assert kannada_number_to_words(5) == "ಐದು"
    assert kannada_number_to_words(16) == "ಹದಿನಾರು"
    assert kannada_number_to_words(20) == "ಇಪ್ಪತ್ತು"
    assert kannada_number_to_words(24) == "ಇಪ್ಪತ್ತನಾಲ್ಕು"
    assert kannada_number_to_words(46) == "ನಲವತ್ತಾರು"
    assert kannada_number_to_words(50) == "ಐವತ್ತು"
    assert kannada_number_to_words(230) == "ಇನ್ನೂರ ಮೂವತ್ತು"
    assert kannada_number_to_words(100) == "ನೂರು"


def test_hindi_and_english_number_to_words():
    """Verify Hindi and English numbers expand accurately."""
    assert hindi_number_to_words(5) == "पाँच"
    assert hindi_number_to_words(46) == "छियालीस"
    assert hindi_number_to_words(230) == "दो सौ तीस"

    assert english_number_to_words(5) == "five"
    assert english_number_to_words(46) == "forty-six"
    assert english_number_to_words(230) == "two hundred thirty"


def test_expand_numbers_and_symbols_kannada():
    """Verify symbols and numbers expand into spoken Kannada so MMS-TTS never drops them."""
    # 230 V
    exp1 = expand_numbers_and_symbols("230 V", "kn")
    assert "ಇನ್ನೂರ ಮೂವತ್ತು" in exp1
    assert "ವೋಲ್ಟ್" in exp1
    assert "230" not in exp1

    # 46 Ω
    exp2 = expand_numbers_and_symbols("46 Ω", "kn")
    assert "ನಲವತ್ತಾರು" in exp2
    assert "ಓಮ್" in exp2
    assert "46" not in exp2

    # 5 A
    exp3 = expand_numbers_and_symbols("5 A", "kn")
    assert "ಐದು" in exp3
    assert "ಆಂಪಿಯರ್" in exp3
    assert "5" not in exp3

    # V = I × R
    exp4 = expand_numbers_and_symbols("V = I × R", "kn")
    assert "ಸಮಾನ" in exp4
    assert "ಗುಣಿಸು" in exp4
    assert "=" not in exp4
    assert "×" not in exp4


# ---------------------------------------------------------------------------
# Zero Devanagari Leakage in Kannada
# ---------------------------------------------------------------------------
def test_kannada_zero_devanagari_rule():
    """Verify automated check for zero Devanagari (U+0900-U+097F) in Kannada text."""
    kannada_clean = "ವೋಲ್ಟೇಜ್ ಕರೆಂಟ್ ಮತ್ತು ರೋಧ"
    devanagari_leak = "ವೋಲ್ಟೇಜ್ वोल्टेज ರೋಧ"

    assert not contains_devanagari(kannada_clean)
    assert contains_kannada(kannada_clean)

    assert contains_devanagari(devanagari_leak)
    sanitized = sanitize_kannada_output(devanagari_leak)
    assert not contains_devanagari(sanitized)


def test_ensure_word_budget():
    """Verify sandhi/samasa condensation (< 8 words) is naturally expanded for schema compliance."""
    condensed_kannada = "ವೋಲ್ಟೇಜ್ ಕರೆಂಟ್ ಮತ್ತು ರೋಧ."  # 4 words
    expanded = ensure_word_budget(condensed_kannada, "kn", min_words=8, max_words=42)
    assert len(expanded.split()) >= 8
    assert "ವೋಲ್ಟೇಜ್" in expanded


# ---------------------------------------------------------------------------
# Zero Double-Padding & Audio Sync Tests
# ---------------------------------------------------------------------------
def test_zero_double_padding_and_audio_length_sync(tmp_path):
    """Verify scene duration matches measured audio directly with zero double-padding."""
    plan = LessonPlan.model_validate_json(GOLDEN_OHMS.read_text(encoding="utf-8"))
    engine = OfflineTTSEngine()

    out_wav = tmp_path / "test_lesson_audio.wav"
    timings = engine.synthesize_all_scenes(plan.scenes, "en", out_wav)

    assert len(timings) == len(plan.scenes)
    cursor = 0.0
    for t in timings:
        # start_sec must equal previous cursor
        assert t["start_sec"] == round(cursor, 3)
        # end_sec must equal start_sec + duration_sec exactly
        assert t["end_sec"] == round(t["start_sec"] + t["duration_sec"], 3)
        cursor = t["end_sec"]

    manifest = build_manifest(plan, timings, "en", str(out_wav.name), TARGET_SR)
    assert manifest["total_sec"] == round(cursor, 3)
    assert 30.0 <= manifest["total_sec"] <= 90.0
    assert out_wav.exists()
    assert out_wav.stat().st_size > 0


# ---------------------------------------------------------------------------
# Golden Manifest Fixture Validation
# ---------------------------------------------------------------------------
def test_golden_manifest_en_conforms_to_contract():
    """Verify fixtures/golden_manifest_en.json matches PLAN.md 4.3 frozen contract."""
    assert GOLDEN_MANIFEST.exists(), "golden_manifest_en.json must exist to unblock Farhan/Ayush"
    data = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))

    assert data["lang"] == "en"
    assert data["sample_rate"] == 24000
    assert data["audio"] == "lesson_audio.wav"
    assert data["total_sec"] == 54.79

    scenes = data["scenes"]
    assert len(scenes) == 5
    assert [s["id"] for s in scenes] == [1, 2, 3, 4, 5]
    assert [s["duration_sec"] for s in scenes] == [9.92, 12.09, 10.78, 12.52, 9.48]
    assert [s["start_sec"] for s in scenes] == [0.0, 9.92, 22.01, 32.79, 45.31]
    assert [s["end_sec"] for s in scenes] == [9.92, 22.01, 32.79, 45.31, 54.79]


# ---------------------------------------------------------------------------
# Captions Generator Tests
# ---------------------------------------------------------------------------
def test_captions_proportional_word_timings():
    """Verify captions compute proportional word timings according to FARHAN_BLUEPRINT.md."""
    text = "Voltage equals Current multiplied by Resistance."
    timings = compute_word_timings(text, scene_start_sec=10.0, scene_dur_sec=8.0)

    words = text.split()
    assert len(timings) == len(words)
    assert timings[0]["word"] == "Voltage"
    assert timings[0]["start_sec"] >= 10.15  # starts after head pad 0.15s
    assert timings[-1]["end_sec"] <= 18.0   # ends within scene duration

    srt = generate_srt([{"start_sec": 0.0, "end_sec": 9.92, "narration": text}])
    assert "-->" in srt
    assert text in srt

    vtt = generate_vtt([{"start_sec": 0.0, "end_sec": 9.92, "narration": text}])
    assert "WEBVTT" in vtt
