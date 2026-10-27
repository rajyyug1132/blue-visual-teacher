"""tests/test_multilingual_sync.py — Verification of cross-language timing synchronization.

Asserts that taking an English lesson plan and generating across all present languages
(English, Hindi, Kannada, Tamil, Bengali) produces:
  - Exact same total duration.
  - Exact same scene durations, start times, and end times.
  - Exact same audio length and frame count via time expansion and compression.
  - Zero timing drift across all languages.
"""

from __future__ import annotations

import json
import math
import os
import wave
from pathlib import Path

import pytest

from localization.tts_engine import (
    OfflineTTSEngine,
    TARGET_SR,
    TAIL_PAD_SEC,
    time_scale_audio,
)
from orchestrator.schema import LessonPlan
from run_pipeline import PRESENT_LANGUAGES, run


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures" / "golden_ohms_law.json"


@pytest.fixture
def isolated_artifact_dir(tmp_path, monkeypatch):
    """Keep run_pipeline.run() out of cache/artifacts, which is the live demo cache.

    run_pipeline.ARTIFACT_DIR points at the real demo directory, so an unpatched
    run() overwrites the Ohm's Law / Photosynthesis / Newton's Third Law artifacts
    that the running product serves.
    """
    import run_pipeline

    monkeypatch.setattr(run_pipeline, "ARTIFACT_DIR", tmp_path)
    return tmp_path


def test_time_scale_audio_compression():
    """Verify audio is compressed in time to match a shorter target duration."""
    sr = TARGET_SR
    pad_samples = int(TAIL_PAD_SEC * sr)
    orig_dur = 8.0
    target_dur = 6.0

    orig_samples = int(round(orig_dur * sr))
    target_samples = int(round(target_dur * sr))

    # Create dummy audio (sine wave + silence pad)
    sine = [0.5 * math.sin(2 * math.pi * 440 * i / sr) for i in range(orig_samples - pad_samples)]
    wav = sine + [0.0] * pad_samples
    assert len(wav) == orig_samples

    # Compress audio to target_samples
    scaled = time_scale_audio(wav, target_samples, sr=sr, tail_pad_samples=pad_samples)
    assert len(scaled) == target_samples
    assert round(len(scaled) / sr, 3) == target_dur

    # Tail pad must be silent
    tail = scaled[-pad_samples:]
    assert all(abs(s) < 1e-5 for s in tail)


def test_time_scale_audio_expansion():
    """Verify audio is expanded in time to match a longer target duration."""
    sr = TARGET_SR
    pad_samples = int(TAIL_PAD_SEC * sr)
    orig_dur = 5.0
    target_dur = 7.5

    orig_samples = int(round(orig_dur * sr))
    target_samples = int(round(target_dur * sr))

    sine = [0.5 * math.sin(2 * math.pi * 440 * i / sr) for i in range(orig_samples - pad_samples)]
    wav = sine + [0.0] * pad_samples
    assert len(wav) == orig_samples

    # Expand audio to target_samples
    scaled = time_scale_audio(wav, target_samples, sr=sr, tail_pad_samples=pad_samples)
    assert len(scaled) == target_samples
    assert round(len(scaled) / sr, 3) == target_dur

    # Tail pad must be silent
    tail = scaled[-pad_samples:]
    assert all(abs(s) < 1e-5 for s in tail)


def test_cross_language_scene_durations_identical(tmp_path):
    """Verify that synthesizing multiple languages with target_durations gives identical manifests."""
    tts = OfflineTTSEngine()
    plan_data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    plan = LessonPlan.model_validate(plan_data)

    # 1. Synthesize English to establish master scene durations
    en_wav = tmp_path / "en.wav"
    en_manifest = tts.synthesize_all_scenes(plan.scenes, "en", en_wav)
    ref_durations = [s["duration_sec"] for s in en_manifest]
    ref_total = en_manifest[-1]["end_sec"]

    assert len(ref_durations) == len(plan.scenes)
    assert 30.0 <= ref_total <= 90.0

    # 2. Synthesize all other present languages with target_durations
    other_langs = [l for l in PRESENT_LANGUAGES if l != "en"]
    for lang in other_langs:
        lang_wav = tmp_path / f"{lang}.wav"
        lang_manifest = tts.synthesize_all_scenes(
            plan.scenes, lang, lang_wav, target_durations=ref_durations
        )

        assert len(lang_manifest) == len(en_manifest)
        # Check every single scene timing matches English reference exactly
        for i in range(len(en_manifest)):
            assert lang_manifest[i]["duration_sec"] == en_manifest[i]["duration_sec"], (
                f"Scene {i+1} duration mismatch in '{lang}': {lang_manifest[i]['duration_sec']} vs {en_manifest[i]['duration_sec']}"
            )
            assert lang_manifest[i]["start_sec"] == en_manifest[i]["start_sec"], (
                f"Scene {i+1} start_sec mismatch in '{lang}': {lang_manifest[i]['start_sec']} vs {en_manifest[i]['start_sec']}"
            )
            assert lang_manifest[i]["end_sec"] == en_manifest[i]["end_sec"], (
                f"Scene {i+1} end_sec mismatch in '{lang}': {lang_manifest[i]['end_sec']} vs {en_manifest[i]['end_sec']}"
            )

        # Check total duration matches exactly
        assert lang_manifest[-1]["end_sec"] == ref_total

        # Check WAV files have the exact same duration and frame count
        with wave.open(str(en_wav), "rb") as w_en, wave.open(str(lang_wav), "rb") as w_lang:
            assert w_lang.getnframes() == w_en.getnframes(), (
                f"WAV frame count mismatch in '{lang}': {w_lang.getnframes()} vs {w_en.getnframes()}"
            )
            assert w_lang.getframerate() == w_en.getframerate() == TARGET_SR


def test_synthesize_multilingual_all_scenes_helper(tmp_path):
    """Verify synthesize_multilingual_all_scenes helper synchronizes multiple plans."""
    tts = OfflineTTSEngine()
    plan_data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    plan = LessonPlan.model_validate(plan_data)

    plans = {lang: plan for lang in PRESENT_LANGUAGES}
    manifests = tts.synthesize_multilingual_all_scenes(plans, tmp_path, reference_lang="en")

    assert set(manifests.keys()) == set(PRESENT_LANGUAGES)
    ref_manifest = manifests["en"]
    ref_total = ref_manifest[-1]["end_sec"]

    for lang, m in manifests.items():
        assert len(m) == len(ref_manifest)
        assert m[-1]["end_sec"] == ref_total
        for s_ref, s_lang in zip(ref_manifest, m):
            assert s_lang["start_sec"] == s_ref["start_sec"]
            assert s_lang["end_sec"] == s_ref["end_sec"]
            assert s_lang["duration_sec"] == s_ref["duration_sec"]


def test_run_pipeline_multilingual_sync(isolated_artifact_dir):
    """Verify run_pipeline.run generates all present languages synchronized to English."""
    artifacts = run(topic=None, langs="all")

    assert set(artifacts.keys()) == set(PRESENT_LANGUAGES)

    manifests = {}
    for lang, out_dir in artifacts.items():
        assert out_dir.exists()
        manifest_file = out_dir / "manifest.json"
        audio_file = out_dir / "lesson_audio.wav"
        vtt_file = out_dir / "captions.vtt"
        srt_file = out_dir / "captions.srt"

        assert manifest_file.exists()
        assert audio_file.exists()
        assert vtt_file.exists()
        assert srt_file.exists()

        m = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifests[lang] = m

    # Compare all manifests to English
    en_m = manifests["en"]
    en_total = en_m["total_sec"]
    en_scenes = en_m["scenes"]

    for lang in ["hi", "kn", "ta", "bn"]:
        lang_m = manifests[lang]
        assert lang_m["total_sec"] == en_total, f"Total duration mismatch in '{lang}'"
        assert len(lang_m["scenes"]) == len(en_scenes)
        for s_en, s_lang in zip(en_scenes, lang_m["scenes"]):
            assert s_lang["start_sec"] == s_en["start_sec"]
            assert s_lang["end_sec"] == s_en["end_sec"]
            assert s_lang["duration_sec"] == s_en["duration_sec"]


def test_multilingual_sync_three_scenarios(isolated_artifact_dir):
    """Verify 3 distinct real-world curriculum scenarios across all 5 present languages."""
    scenarios = ["Ohm's Law", "Photosynthesis", "Newton's Third Law"]
    for topic in scenarios:
        topic_arg = topic if topic != "Ohm's Law" else None
        artifacts = run(topic=topic_arg, langs="all")
        assert set(artifacts.keys()) == set(PRESENT_LANGUAGES)

        en_dir = artifacts["en"]
        en_wav = en_dir / "lesson_audio.wav"
        en_man = json.loads((en_dir / "manifest.json").read_text(encoding="utf-8"))
        with wave.open(str(en_wav), "rb") as w_en:
            en_frames = w_en.getnframes()
        en_total_sec = en_man["total_sec"]

        for lang in ["hi", "kn", "ta", "bn"]:
            lang_dir = artifacts[lang]
            lang_wav = lang_dir / "lesson_audio.wav"
            lang_man = json.loads((lang_dir / "manifest.json").read_text(encoding="utf-8"))
            with wave.open(str(lang_wav), "rb") as w_lang:
                lang_frames = w_lang.getnframes()

            # Exact frame count and total duration match
            assert lang_frames == en_frames, f"Frame count drift in topic '{topic}', lang '{lang}'"
            assert lang_man["total_sec"] == en_total_sec, f"Total duration drift in topic '{topic}', lang '{lang}'"

            # Exact scene-by-scene duration match
            for s_en, s_lang in zip(en_man["scenes"], lang_man["scenes"]):
                assert s_lang["start_sec"] == s_en["start_sec"]
                assert s_lang["end_sec"] == s_en["end_sec"]
                assert s_lang["duration_sec"] == s_en["duration_sec"]
