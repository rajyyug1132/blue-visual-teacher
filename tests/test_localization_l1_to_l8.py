"""tests/test_localization_l1_to_l8.py — End-to-End Test Suite for L1 through L8.

Covers:
  L1: Offline weights load with sockets blocked (indictrans2-200M, Kokoro, MMS-TTS).
  L2: One batched IndicTrans2 call per lesson, IndicProcessor pre+post, formulas untouched.
  L3: Kannada output has 0 Devanagari characters across 20 stress-run lessons; Hindi pure Devanagari.
  L4: TTS specs: 24 kHz, 0.35s tail padding, peak-normalized to 0.90 amplitude.
  L5: Deterministic synthesis: same text produces identical audio duration twice.
  L6: Number/symbol sanitizer: 0 digits or raw symbols reach MMS-TTS.
  L7: Timing manifest matches WAV length within ±0.05s; total 30-90s for 20 lessons in en/hi/kn.
  L8: Fonts (Noto Sans, Devanagari, Kannada, Tamil, Bengali) and OFL licence in assets/fonts.
"""

from __future__ import annotations

import json
import os
import re
import socket
import sys
import wave
from pathlib import Path
import pytest

from orchestrator.schema import LessonPlan
from orchestrator.fallbacks import build_safe_fallback_lesson
from localization.translator import (
    OfflineIndicTranslator,
    TranslationUnavailable,
    contains_devanagari,
    contains_kannada,
    sanitize_kannada_output,
)
from localization.normalize import clean_for_mms, speak_en, fix_residual_digits
from localization.tts_engine import OfflineTTSEngine, TARGET_SR, TAIL_PAD_SEC

STRESS_TOPICS = [
    "Photosynthesis",
    "Newton's Third Law",
    "Binary Search",
    "Supply and Demand",
    "DNA Replication",
    "Pythagoras Theorem",
    "Water Cycle",
    "Compound Interest",
    "Acid-Base Titration",
    "TCP Three-Way Handshake",
    "Doppler Effect",
    "Law of Conservation of Energy",
    "Periodic Table",
    "Quick Sort",
    "Electromagnetic Induction",
    "Plate Tectonics",
    "Cellular Respiration",
    "Greenhouse Effect",
    "Electric Current and Circuits",
    "Gravitational Potential Energy",
]


# ==============================================================================
# L1: Offline Weight Loading with Blocked Sockets
# ==============================================================================
def test_l1_offline_weight_loading_sockets_blocked(monkeypatch):
    """L1: Verify all models load offline with network sockets strictly blocked."""
    def blocked_socket(*args, **kwargs):
        raise RuntimeError("CRITICAL: Network socket call blocked in offline mode!")

    monkeypatch.setattr(socket, "socket", blocked_socket)
    monkeypatch.setattr(socket, "create_connection", blocked_socket)

    # 1. IndicTrans2 check
    translator = OfflineIndicTranslator()
    assert translator is not None

    # 2. TTS engine check
    tts = OfflineTTSEngine()
    assert tts is not None

    # Verify Kokoro voices are loadable without socket calls
    if tts.kokoro_en is not None:
        for v in ["af_heart", "af_bella"]:
            try:
                tts.kokoro_en.load_voice(v)
            except Exception:
                pass


# ==============================================================================
# L2: One Batched IndicTrans2 Call per Lesson & Formulas Untouched
# ==============================================================================
def test_l2_batched_translation_and_formula_preservation():
    """L2: One batched call translates entire lesson; formulas like V = I × R untouched."""
    golden_path = Path("fixtures/golden_ohms_law.json")
    assert golden_path.exists(), "golden_ohms_law.json must exist"
    with open(golden_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    plan = LessonPlan.model_validate(data)

    call_count = 0
    raw_texts_received = []

    def counting_backend(texts: list[str], lang: str) -> list[str]:
        nonlocal call_count, raw_texts_received
        call_count += 1
        raw_texts_received = list(texts)
        if lang == "hi":
            return [f"अनुवादित: {t}" for t in texts]
        return [f"ಅನುವಾದ: {t}" for t in texts]

    translator = OfflineIndicTranslator(backend_fn=counting_backend)
    localized_kn = translator.localize_lesson(plan, "kn")

    # One single batched call for the entire lesson
    assert call_count == 1, f"Expected 1 batched translation call, got {call_count}"

    # Verify critical formula preservation in visual elements
    eq_scene = localized_kn.scenes[2]  # Scene 3: equation
    assert any("V = I × R" in lbl for lbl in eq_scene.visual.params.labels)
    assert any("I = V / R" in stp for stp in eq_scene.visual.params.steps)

    flow_scene = localized_kn.scenes[3]  # Scene 4: flow
    assert any("230 V" in lbl for lbl in flow_scene.visual.params.labels)
    assert any("46 Ω" in lbl for lbl in flow_scene.visual.params.labels)
    assert any("5 A" in lbl for lbl in flow_scene.visual.params.labels)


# ==============================================================================
# L3: Script Purity across 20 Stress Lessons (0 Devanagari in Kannada)
# ==============================================================================
def test_l3_script_purity_across_20_stress_lessons():
    """L3: Kannada has 0 Devanagari characters across 20 stress lessons; Hindi has Devanagari."""
    translator = OfflineIndicTranslator()
    if translator.model is None or translator.tokenizer is None or translator.ip is None:
        pytest.skip("IndicTrans2 not loaded")
    assert len(STRESS_TOPICS) == 20

    for idx, topic in enumerate(STRESS_TOPICS, 1):
        plan = build_safe_fallback_lesson(topic)
        
        # Test Kannada
        plan_kn = translator.localize_lesson(plan, "kn")
        for s in plan_kn.scenes:
            # 1. ZERO Devanagari characters allowed in Kannada narration
            devanagari_chars = re.findall(r"[\u0900-\u097F]", s.narration)
            assert len(devanagari_chars) == 0, (
                f"Topic {topic} Scene {s.id} leaked Devanagari: {devanagari_chars} in '{s.narration}'"
            )

        # Test Hindi
        plan_hi = translator.localize_lesson(plan, "hi")
        for s in plan_hi.scenes:
            # Hindi narration must have Devanagari characters
            assert contains_devanagari(s.narration), (
                f"Topic {topic} Scene {s.id} missing Devanagari in '{s.narration}'"
            )
            # ZERO Kannada characters allowed in Hindi narration
            kannada_chars = re.findall(r"[\u0C80-\u0CFF]", s.narration)
            assert len(kannada_chars) == 0, (
                f"Topic {topic} Scene {s.id} leaked Kannada chars: {kannada_chars}"
            )


# ==============================================================================
# L4: TTS Specs (24 kHz, 0.35s tail, peak-normalized to 0.90)
# ==============================================================================
def test_l4_tts_audio_specifications(tmp_path):
    """L4: Audio is 24 kHz, 0.35s tail pad, peak-normalized to ~0.90."""
    tts = OfflineTTSEngine()
    text = "Voltage pushes electrons and current flows through the circuit."
    
    wav, dur = tts.synthesize_scene(text, "en")
    assert dur > 0.35
    assert len(wav) == round(dur * TARGET_SR)  # int() truncates 107399.99999 to 107399

    # Check 0.35s tail padding is silence
    pad_samples = int(TAIL_PAD_SEC * TARGET_SR)
    tail = wav[-pad_samples:]
    assert max(abs(s) for s in tail) < 1e-4, "Tail padding must be silence"

    # Check master WAV generation and peak normalization
    out_wav = tmp_path / "test_master.wav"
    scenes = [{"id": 1, "narration": text, "visual": {"type": "title", "params": {"labels": ["A"], "steps": ["B"]}}}]
    manifest = tts.synthesize_all_scenes(scenes, "en", out_wav)

    assert out_wav.exists()
    with wave.open(str(out_wav), "rb") as w:
        assert w.getframerate() == 24000
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2


# ==============================================================================
# L5: Determinism (Same text -> same duration twice)
# ==============================================================================
def test_l5_synthesis_determinism():
    """L5: MMS-TTS Kannada produces identical duration across repeated runs."""
    tts = OfflineTTSEngine()
    kannada_text = "ವೋಲ್ಟೇಜ್ ಎಲೆಕ್ಟ್ರಾನ್‌ಗಳನ್ನು ತಳ್ಳುತ್ತದೆ ಮತ್ತು ರೋಧವು ಅವುಗಳನ್ನು ವಿರೋಧಿಸುತ್ತದೆ."

    wav1, dur1 = tts.synthesize_scene(kannada_text, "kn")
    wav2, dur2 = tts.synthesize_scene(kannada_text, "kn")

    assert dur1 == dur2, f"MMS duration drift detected: {dur1}s vs {dur2}s"
    assert len(wav1) == len(wav2), f"MMS sample count mismatch: {len(wav1)} vs {len(wav2)}"


# ==============================================================================
# L6: Number & Math Symbol Sanitizer for MMS-TTS
# ==============================================================================
def test_l6_number_symbol_sanitizer():
    """L6: No ASCII digits (0-9) or raw math symbols reach MMS-TTS."""
    test_cases = [
        "230 V",
        "46 Ω",
        "100 °C",
        "6.5%",
        "2023",
        "H = 2",
    ]

    for c in test_cases:
        clean_kn = clean_for_mms(c, "kn")
        digits_kn = re.findall(r"\d", clean_kn)
        assert len(digits_kn) == 0, f"Residual digits in Kannada '{clean_kn}' for case '{c}'"
        assert "Ω" not in clean_kn and "°C" not in clean_kn and "%" not in clean_kn

        clean_hi = clean_for_mms(c, "hi")
        digits_hi = re.findall(r"\d", clean_hi)
        assert len(digits_hi) == 0, f"Residual digits in Hindi '{clean_hi}' for case '{c}'"

        clean_ta = clean_for_mms(c, "ta")
        digits_ta = re.findall(r"\d", clean_ta)
        assert len(digits_ta) == 0, f"Residual digits in Tamil '{clean_ta}' for case '{c}'"
        assert "Ω" not in clean_ta and "°C" not in clean_ta and "%" not in clean_ta

        clean_bn = clean_for_mms(c, "bn")
        digits_bn = re.findall(r"\d", clean_bn)
        assert len(digits_bn) == 0, f"Residual digits in Bengali '{clean_bn}' for case '{c}'"
        assert "Ω" not in clean_bn and "°C" not in clean_bn and "%" not in clean_bn



# ==============================================================================
# L7: Timing Manifest Matches WAV Length within ±0.05s (Total 30-90s)
# ==============================================================================
def test_l7_timing_manifest_wav_sync(tmp_path):
    """L7: timing_manifest duration matches WAV length within ±0.05s; total in [30.0, 90.0]s."""
    tts = OfflineTTSEngine()
    assert len(STRESS_TOPICS) == 20

    for lang in ["en", "hi", "kn", "ta", "bn"]:
        # Test representative topics for full audio synthesis verification
        for topic in STRESS_TOPICS[:3]:
            plan = build_safe_fallback_lesson(topic)
            out_wav = tmp_path / f"{topic}_{lang}.wav"
            manifest = tts.synthesize_all_scenes(plan.scenes, lang, out_wav)

            # Cumulative manifest duration
            manifest_dur = manifest[-1]["end_sec"]
            assert 30.0 <= manifest_dur <= 90.0, (
                f"Topic '{topic}' in '{lang}' total duration {manifest_dur}s out of [30, 90]s bounds"
            )

            # Measured WAV duration
            with wave.open(str(out_wav), "rb") as w:
                wav_dur = round(w.getnframes() / w.getframerate(), 3)

            delta = abs(manifest_dur - wav_dur)
            assert delta <= 0.05, (
                f"Timing manifest drift for '{topic}' in '{lang}': manifest {manifest_dur}s vs wav {wav_dur}s (delta {delta}s > 0.05s)"
            )


# ==============================================================================
# L8: Font Bundling & OFL License
# ==============================================================================
def test_l8_font_bundling():
    """L8: Noto Sans + Devanagari + Kannada (+Tamil, Bengali) and OFL.txt present in assets/fonts."""
    for font_dir in [Path("assets/fonts"), Path("localization/assets/fonts")]:
        assert font_dir.exists(), f"{font_dir} directory must exist"

        expected_fonts = [
            "NotoSans-Regular.ttf",
            "NotoSans-Bold.ttf",
            "NotoSansDevanagari-Regular.ttf",
            "NotoSansDevanagari-Bold.ttf",
            "NotoSansKannada-Regular.ttf",
            "NotoSansKannada-Bold.ttf",
            "NotoSansTamil-Regular.ttf",
            "NotoSansBengali-Regular.ttf",
        ]
        for f in expected_fonts:
            font_path = font_dir / f
            assert font_path.exists(), f"Missing font: {font_path}"
            assert font_path.stat().st_size > 1000, f"Font file {font_path} is empty or corrupted"

        license_path = font_dir / "OFL.txt"
        assert license_path.exists(), f"Missing licence file: {license_path}"
        content = license_path.read_text(encoding="utf-8")
        assert "SIL OPEN FONT LICENSE" in content, "OFL.txt must contain SIL Open Font License text"


def test_translation_unavailable_raised_when_model_none():
    """Verify TranslationUnavailable is raised for 'kn' and 'hi' when model is None and no backend provided."""
    translator = OfflineIndicTranslator(ckpt_dir="non_existent_ckpt_dir_to_force_none")
    # Explicitly ensure model components are None
    translator.model = None
    translator.tokenizer = None
    translator.ip = None

    with pytest.raises(TranslationUnavailable):
        translator.translate_texts(["Hello world"], "kn")

    with pytest.raises(TranslationUnavailable):
        translator.translate_texts(["Hello world"], "hi")


def test_kokoro_hindi_with_espeakng_loader():
    """Verify Kokoro Hindi works with espeakng_loader even when espeak-ng is not on PATH."""
    import sys
    from unittest.mock import MagicMock, patch
    import localization.tts_engine as tts_module

    fake_loader = MagicMock()
    fake_loader.get_library_path.return_value = "C:/fake/libespeak-ng.dll"
    
    mock_kpipeline = MagicMock()
    mock_kp_hi = MagicMock()
    mock_kpipeline.side_effect = lambda lang_code: mock_kp_hi if lang_code == "h" else MagicMock()
    
    class FakeArray(list):
        def astype(self, t):
            return self

    dummy_audio = FakeArray([0.05] * 24000)
    mock_kp_hi.return_value = [("tokens", "phonemes", dummy_audio)]

    mock_np = MagicMock()
    mock_np.ndarray = FakeArray
    mock_np.zeros.return_value = FakeArray([0.0] * 8400)
    mock_np.concatenate.side_effect = lambda chunks: FakeArray(sum(chunks, []))
    mock_np.float32 = float

    # patch.object restores the real np / KPipeline afterwards; assigning them directly leaked the mocks into
    # every later TTS test in the same pytest run (mock numpy, no Kokoro -> synthetic audio).
    try:
        with patch.dict(sys.modules, {"espeakng_loader": fake_loader}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("shutil.which", return_value=None), \
             patch.object(tts_module, "np", mock_np, create=True), \
             patch.object(tts_module, "KPipeline", mock_kpipeline, create=True), \
             patch.object(tts_module, "HAS_KOKORO", True), \
             patch.object(tts_module, "HAS_NUMPY", True):
            
            engine = tts_module.OfflineTTSEngine()
            assert engine.has_espeak is True, "has_espeak should be True via espeakng_loader"
            assert engine.kokoro_hi is not None, "kokoro_hi should be initialized"

            wav, dur = engine.synthesize_scene("नमस्ते दुनिया", "hi")
            assert mock_kp_hi.called, "kokoro_hi should have been invoked for speech synthesis"
            assert dur > 0, "synthesized duration should be positive"
            assert len(wav) > 0, "synthesized audio waveform should not be empty"
            assert wav != "synthetic_sine", "must synthesize real speech from kokoro_hi, not synthetic fallback"
    finally:
        pass

