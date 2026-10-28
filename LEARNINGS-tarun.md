# LEARNINGS-tarun.md — Localization Engineering Log & Priority Tracking

## Overview
Owner: **Tarun** (`localization/`)
Deliverables: Offline translation (`translator.py`), dual-engine TTS (`tts_engine.py`), captions (`captions.py`), normalization & number sanitization (`normalize.py`), and typography (`assets/fonts/`).

---

## L1–L8 Verification Matrix & Engineering Learnings

### L1: Offline Model Weights Loading with Sockets Blocked
- **Requirement**: `indictrans2-200M`, `Kokoro-82M` + voicepacks (`af_heart`, `af_bella`, `hf_alpha`, `hm_omega`), `mms-tts-kan` (plus bonus `tam`, `ben`) load with sockets monkeypatched/blocked.
- **Learning**: `HF_HOME` must point to the local cache directory (set BVT_HF_HOME (or HF_HOME) to your local cache). Setting `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` alongside `local_files_only=True` guarantees zero network socket requests. All voicepacks (`.pt`) and checkpoint tensors are resident on disk.
- **Status**: PASS

### L2: Batched IndicTrans2 Translation with Preserved Formulas
- **Requirement**: Single batched `IndicTrans2` call per lesson plan; `IndicProcessor.preprocess_batch` and `postprocess_batch` applied; mathematical expressions (e.g., `V = I × R`, `230 V`, `46 Ω`) untouched.
- **Learning**: Flattening the lesson title, scene narrations, visual labels, and steps into a single batch list maximizes throughput on CPU/GPU. Spans matching `PROTECT` regex patterns are replaced with double-bracket placeholders (`[[PH_i]]`), preserved during NMT translation, and cleanly restored.
- **Status**: PASS

### L3: Script Purity across 20 Stress Lessons (Kannada & Hindi)
- **Requirement**: Kannada (`kn`) outputs must contain ONLY Kannada block characters (`\u0C80-\u0CFF`) and exactly ZERO Devanagari characters (`\u0900-\u097F`). Hindi (`hi`) outputs must contain Devanagari characters.
- **Learning**: Raw IndicTrans2 generates in unified Devanagari space. Without `IndicProcessor.postprocess_batch(lang="kan_Knda")`, Kannada text leaks Devanagari glyphs. A secondary `sanitize_kannada_output()` pass strips any residual unmapped Devanagari codepoints to guarantee 100% script purity across all 20 stress topics.
- **Status**: PASS

### L4: Dual-Engine TTS Audio Specifications
- **Requirement**: Kokoro-82M for EN (`af_heart`), Kokoro-82M / MMS fallback for HI, MMS-TTS for KN with `torch.manual_seed(42)`. Standardized 24 kHz audio, 0.35s tail padding, peak-normalized to 0.90 amplitude.
- **Learning**: Meta VITS outputs 16 kHz audio. Resampling via `scipy.signal.resample_poly` with up=3, down=2 converts cleanly to 24 kHz matching Kokoro's native output. Peak normalization to `0.90` prevents clipping distortion.
- **Status**: PASS

### L5: Synthesis Determinism
- **Requirement**: Synthesizing the exact same text twice must yield identical audio duration down to the millisecond ($\Delta t = 0.000$s).
- **Learning**: Meta VITS duration predictor uses stochastic sampling. Explicitly seeding PyTorch with `torch.manual_seed(42)` immediately prior to the model forward pass eliminates duration drift across repeated runs.
- **Status**: PASS

### L6: Number and Math Symbol Sanitizer for MMS-TTS
- **Requirement**: Zero ASCII digits (`0-9`) or math symbols (`=`, `+`, `-`, `×`, `÷`, `Ω`, `%`, `°C`) reach MMS-TTS.
- **Learning**: Meta MMS-TTS lacks token mappings for ASCII digits and math glyphs, causing silent dropped numbers. `clean_for_mms()` expands numbers into natural Kannada words (e.g., `230` $\rightarrow$ `ಇನ್ನೂರ ಮೂವತ್ತು`) and replaces math symbols with spoken phonetic words.
- **Status**: PASS

### L7: Timing Manifest and Audio Duration Sync (30–90s Window)
- **Requirement**: `timing_manifest` cumulative duration matches master WAV duration within $\pm 0.05$s. Total lesson duration lands strictly in [30.0, 90.0] seconds across 20 stress topics.
- **Learning**: Eliminating double-padding ensures `scene.duration_sec` matches the measured audio length (including the 0.35s tail pad). Cumulative `start_sec` and `end_sec` align with the master WAV file.
- **Status**: PASS

### L8: Typography & Font Bundling
- **Requirement**: Noto Sans, Noto Sans Devanagari, Noto Sans Kannada, Noto Sans Tamil, Noto Sans Bengali, and SIL Open Font License 1.1 (`OFL.txt`) bundled in `assets/fonts/` and `localization/assets/fonts/`. Zero external CDN calls.
- **Learning**: Local TTF files provide offline font rendering and complex text shaping (ligatures, virama) inside headless Chromium / Playwright.
- **Status**: PASS
