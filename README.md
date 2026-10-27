# Blue Visual Teacher

Type a concept, get a narrated, animated 30–90 second lesson that plays in the browser and downloads as an MP4, in
English, Hindi or Kannada. Everything runs on the laptop: no cloud AI, no CDN, Wi-Fi can be off. The local LLM only
returns lesson data (JSON); all drawing code is ours.

## Architecture

```
topic ──> classify (formula?) ──> plan (Ollama qwen2.5:3b, schema-constrained JSON, English)
            │                        └─ guard: arithmetic check, spoken-number audit, ladder
            │                           3b retry -> 7b escalation -> qualitative -> safe template
            ▼
      IndicTrans2-200M + IndicProcessor (one batched call per language)
            ▼
      TTS per scene: Kokoro-82M (EN/HI) · MMS-TTS (KN) -> 24 kHz WAV + 0.35 s tail, measured durations
            ▼
      duration gate (30–90 s) ──> manifest.json (scene start/end from real audio)
            ▼
      renderer/player.html: window.renderAtTime(t) on a 1280x720 canvas (pure function of t)
            ▼
      Playwright frames @20 fps ──> FFmpeg image2pipe ──> lesson.mp4 (h264 yuv420p + AAC)
```

Code map: `orchestrator/` (planner, guard, cache, pipeline) · `localization/` (translation, TTS, captions) ·
`renderer/` (canvas engine, 8 templates) · `web/` (UI) · `exporter/` (MP4 export, FastAPI, harness).

## Run it offline

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # once, online
python -m playwright install chromium                                    # once, online
python -c "from localization.warmup import run_all_warmups; run_all_warmups()"  # caches models and voices, online
./run_demo.sh            # or run_demo.ps1 on Windows; then open http://127.0.0.1:8000
```

`run_demo` sets `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `OLLAMA_MAX_LOADED_MODELS=1`, starts Ollama only if it
is not running, pins the planner with `keep_alive=-1`, loads translator and TTS once, then serves the app.
`python scripts/precache.py` pre-generates the 10 example topics so the first demo clicks are instant.

Checks: `python -m pytest tests/` (includes `tests/test_e2e_offline.py`, which blocks outbound sockets) and
`python -m orchestrator.done_checks` (BLUEPRINT DONE list D1–D10, evidence in `logs/`).

## Models and licenses

| Component | Model / package | Role | License | Notes |
|---|---|---|---|---|
| LLM planner | qwen2.5:3b (escalation qwen2.5:7b) via Ollama | English JSON lesson planning | Apache 2.0 (Qwen2.5 3B: Qwen Research License) | Runs locally through the Ollama daemon; no external API |
| Indic translation | ai4bharat/indictrans2-en-indic-dist-200M + IndicTransToolkit | English to Hindi, Kannada (Tamil, Telugu) | MIT | One batched call per language; formulas protected from translation |
| EN and HI speech | hexgrad/Kokoro-82M + misaki + espeak-ng | 24 kHz speech synthesis | Apache 2.0 (espeak-ng: GPL-3.0, invoked as a separate program) | Voices af_heart (EN), hf_alpha (HI) |
| KN speech | facebook/mms-tts-kan (VITS) | 16 kHz speech, resampled to 24 kHz | CC-BY-NC 4.0 | Non-commercial; fine for the hackathon, swap for ai4bharat/indic-parler-tts (Apache 2.0) commercially |
| Indic typography | Noto Sans, Noto Sans Devanagari, Noto Sans Kannada (+ Tamil, Bengali) | Script shaping on the canvas | SIL Open Font License 1.1 | Bundled in assets/fonts (OFL.txt included); the app serves them at /renderer/assets/fonts, zero CDN calls |
| Video and web stack | Playwright (Chromium), FFmpeg (libx264), FastAPI, Pydantic | Frame capture, MP4 muxing, API, schema validation | Apache 2.0 / LGPL-GPLv2+ (libx264 GPL) / MIT / MIT | Invoked locally; libx264 via the FFmpeg binary |

## Design decisions

- **Audio is the master clock.** TTS runs before rendering; each scene lasts exactly as long as its measured audio
  (the 0.35 s tail is inside the WAV, used for the visual transition). No drift by construction.
- **Deterministic renderer.** `renderAtTime(t)` is a pure function of time: no `setInterval`, no unseeded random,
  no clock reads. The same frame twice gives the same pixels, so export and preview match.
- **Data, never code, from the LLM.** Ollama is constrained by `LessonPlan.model_json_schema()`; Pydantic validates.
- **Numbers are verified, not trusted.** A worked example carries `check {expr, result}`; Python evaluates it with an
  AST whitelist (never `eval`), fixes a wrong result where it is stated, and makes the narration say the answer.
- **English planning, Indic output.** The small model plans in English; IndicTrans2 translates once per language.
- **Two caches.** Tier 1: the English plan by topic (switching language skips the LLM). Tier 2: finished artifacts
  by (topic, language) — a repeat request is served instantly.

## Known limits

- Descriptive topics (history, geography, processes) carry no numbers: the planner blocks digits, number words
  above ten, units and formulas there; only dates are allowed.
- Numeric worked examples are arithmetic-checked, but formulas outside a verified bank are not asserted as fact: a
  3B model can still pick a wrong formula for an uncommon topic.
- Hindi speech needs espeak-ng installed on the machine (Kokoro's Hindi phonemizer); without it Hindi is hidden.
- Measured numbers live in `logs/` and `STATUS.md`; this README does not claim results the logs don't show.

## Team

Yyug (orchestrator), Tarun (localization), Farhan (renderer and UI), Ayush (export, API, tests).
