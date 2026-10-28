"""D4 + D5 with the real models (IndicTrans2-200M, Kokoro-82M, MMS-TTS-kan). Skips with a reason when absent.

D4: one batched IndicTrans2 call per lesson, KN narration in the Kannada block with zero Devanagari, formulas untouched.
D5: 24 kHz mono WAV, 0.35 s silent tail per scene, same input -> same duration twice (Kokoro EN, MMS KN/TA/BN seed 42),
    Kokoro HI when espeak-ng is installed. TA and BN skip until facebook/mms-tts-tam and mms-tts-ben are cached.
"""
import os
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from orchestrator.schema import LessonPlan  # noqa: E402

FIXTURE = ROOT / "fixtures" / "golden_ohms_law.json"
FORMULAS = ["V = I × R", "I = V / R", "R = V / I"]


def plan() -> LessonPlan:
    return LessonPlan.model_validate_json(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def translator():
    pytest.importorskip("torch")
    pytest.importorskip("IndicTransToolkit")
    from localization.translator import OfflineIndicTranslator
    tr = OfflineIndicTranslator()
    if tr.model is None or tr.ip is None:
        pytest.skip("IndicTrans2 weights or IndicProcessor not available")
    return tr


@pytest.fixture(scope="module")
def tts():
    pytest.importorskip("torch")
    from localization.tts_engine import OfflineTTSEngine
    return OfflineTTSEngine()


def test_d4_kannada_is_batched_kannada_only_and_keeps_formulas(translator, monkeypatch):
    calls = []
    real = translator._raw_translate_batch
    monkeypatch.setattr(translator, "_raw_translate_batch",
                        lambda texts, lang: calls.append(len(texts)) or real(texts, lang))
    import time
    t0 = time.perf_counter()
    p = plan()
    out = translator.localize_lesson(p, "kn")
    elapsed = time.perf_counter() - t0
    n_strings = 1 + sum(1 + len(s.visual.params.labels) + len(s.visual.params.steps) for s in p.scenes)
    # One batched call carries the whole lesson; later calls only repair protected spans (1-2 strings each).
    assert calls and calls[0] >= len(p.scenes) * 2, f"first call is not the lesson batch: {calls} ({n_strings} strings)"
    assert all(c <= 4 for c in calls[1:]), f"follow-up calls should be small repairs: {calls}"
    print(f"translate kn: batch of {calls[0]} + {len(calls) - 1} repair calls, {elapsed:.1f}s")
    narration = " ".join(s.narration for s in out.scenes)
    kn = sum("ಀ" <= c <= "೿" for c in narration)
    dev = sum("ऀ" <= c <= "ॿ" for c in narration)
    assert kn > 50 and dev == 0, (kn, dev, narration[:200])
    shown = [t for s in out.scenes for t in s.visual.params.labels + s.visual.params.steps]
    for f in FORMULAS:
        assert f in shown, f"formula {f!r} changed by translation: {shown}"


def test_d4_hindi_is_devanagari(translator):
    out = translator.localize_lesson(plan(), "hi")
    narration = " ".join(s.narration for s in out.scenes)
    assert sum("ऀ" <= c <= "ॿ" for c in narration) > 50


def read_wav(path: Path):
    import numpy as np
    with wave.open(str(path)) as w:
        rate, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    dtype = {2: "<i2", 4: "<i4"}[width]
    return rate, ch, np.frombuffer(raw, dtype=dtype).astype("float32") / (2 ** (8 * width - 1))


SCENES_EN = plan().scenes[:2]


def _engine_ready(tts, lang):
    if lang == "en" and tts.kokoro_en is None:
        pytest.skip("Kokoro-82M (EN) not loaded")
    if lang == "hi" and tts.kokoro_hi is None:
        pytest.skip("Kokoro Hindi needs espeak-ng installed (human step)")
    if lang == "kn" and "kn" not in tts.mms_models:
        pytest.skip("facebook/mms-tts-kan not loaded")
    if lang == "ta" and "ta" not in tts.mms_models:
        pytest.skip("facebook/mms-tts-tam not loaded")
    if lang == "bn" and "bn" not in tts.mms_models:
        pytest.skip("facebook/mms-tts-ben not loaded")


_MMS_LINES = {
    "kn": (
        "ನಿಮ್ಮ ಫೋನ್ ಚಾರ್ಜರ್ ವೇಗವಾಗಿ ಚಾರ್ಜ್ ಮಾಡುವಾಗ ಏಕೆ ಬಿಸಿಯಾಗುತ್ತದೆ ಎಂದು ಯೋಚಿಸಿದ್ದೀರಾ?",
        "ಮನೆಯ ಮಾಳಿಗೆಯ ಮೇಲಿನ ನೀರಿನ ಟ್ಯಾಂಕ್ ಬಗ್ಗೆ ಯೋಚಿಸಿ. ನೀರಿನ ಎತ್ತರ ವೋಲ್ಟೇಜ್ ಆಗಿದೆ.",
    ),
    "ta": (
        "ஓம் விதியின்படி ஒரு கடத்தியின் வழியே பாயும் மின்னோட்டம் மின்னழுத்த வேறுபாட்டிற்கு நேர்விகிதத்தில் இருக்கும்.",
        "மின்னோட்டம் மின்னழுத்தத்தை மின்தடையால் வகுத்தால் கிடைக்கும்.",
    ),
    "bn": (
        "ওহমের সূত্র অনুসারে একটি পরিবাহীর মধ্য দিয়ে প্রবাহিত বিদ্যুৎ প্রবাহ বিভব পার্থক্যের সমানুপাতিক।",
        "বিদ্যুৎ প্রবাহ রোধ দিয়ে বিভবকে ভাগ করলে পাওয়া যায়।",
    ),
}


def _mms_scenes(lang):
    p = plan().model_copy(deep=True)
    p.scenes[0].narration = _MMS_LINES[lang][0]
    p.scenes[1].narration = _MMS_LINES[lang][1]
    return p.scenes[:2]


@pytest.mark.parametrize("lang", ["en", "kn", "hi", "ta", "bn"])
def test_d5_tts_is_24khz_with_tail_and_deterministic(tts, lang, tmp_path):
    _engine_ready(tts, lang)
    scenes = SCENES_EN if lang in ("en", "hi") else _mms_scenes(lang)
    first = tts.synthesize_all_scenes(scenes, lang, tmp_path / "a.wav")
    second = tts.synthesize_all_scenes(scenes, lang, tmp_path / "b.wav")
    assert [m["duration_sec"] for m in first] == [m["duration_sec"] for m in second], "same input, different duration"
    rate, ch, audio = read_wav(tmp_path / "a.wav")
    assert (rate, ch) == (24000, 1)
    assert abs(len(audio) / rate - first[-1]["end_sec"]) < 0.02
    for m in first:  # every scene ends with >= 0.35 s of near-silence (the tail), counted once
        end = int(m["end_sec"] * rate)
        tail = audio[end - int(0.35 * rate):end]
        assert len(tail) and float(abs(tail).max()) < 0.02, (m["id"], float(abs(tail).max()))
    for a, b in zip(first, first[1:]):
        assert a["end_sec"] == pytest.approx(b["start_sec"], abs=1e-6)
