# PLAN.md — Blue Visual Teacher (Unlox Codestorm, 24h)

Control document for the whole team and for every Claude Code session.
Reference code lives in `BLUEPRINT.md` (sections 1.2, 1.3, 2.3, 2.4, 3.1, 3.2, 5.1). This file says WHAT to build, WHO owns it, and WHEN it must work. If the two disagree, this file wins.

---

## 0. Mission

Student types a concept -> system produces a narrated, animated lesson of **30-90 s** that plays in the browser and exports as **MP4**. Works in **English + at least 2 Indian languages** (Hindi + Kannada, bonus Tamil/Telugu). **Fully offline, no external AI APIs** (not even cloud voice or translation). The LLM returns **data (JSON), never code**.

Judging: working end to end 25 | teaching quality 20 | visuals 15 | languages 15 | engineering 15 | speed 10.
Final demo: live, Wi-Fi OFF, topic + language chosen by judges.

Rule that makes sync trivial: **narration audio is generated first; each scene lasts exactly as long as its audio.**

## 1. Pipeline

```
topic
 -> plan_lesson (Ollama, English JSON, schema-constrained)      [orchestrator]
 -> validate (pydantic) -> 1 retry -> safe fallback template    [orchestrator]
 -> localize (IndicTrans2, ONE batched call per language)       [localization]
 -> TTS per scene (Kokoro EN/HI, MMS-TTS KN/TA/TE)              [localization]
 -> manifest.json: per-scene start/end from real audio length   [localization]
 -> browser player renders renderAtTime(t) on 1280x720 canvas   [renderer]
 -> Playwright captures frames @20fps -> FFmpeg mux -> MP4      [exporter]
```

Artifacts are cached by `(topic_slug, lang)`; the English plan is cached by `topic_slug` so a second language skips the LLM entirely.

## 2. Repo layout and ownership

```
CLAUDE.md                      (rules, section 3)
PLAN.md  BLUEPRINT.md
orchestrator/    schema.py planner.py prompts.py cache.py fallbacks.py pipeline.py   OWNER: Yyug
localization/    translator.py tts_engine.py captions.py assets/fonts/               OWNER: Tarun
renderer/        player.html engine.js templates.js assets/fonts/                    OWNER: Farhan
exporter/        export_mp4.py app.py test_harness.py                                OWNER: Ayush
fixtures/        golden_ohms_law.json  golden_manifest_en.json
cache/           plans/  artifacts/{slug}_{lang}/{manifest.json,lesson_audio.wav,lesson.mp4}
tests/           test_e2e_offline.py
run_demo.sh      (sets HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1, warms models, starts app)
README.md        (setup, architecture, licenses table from BLUEPRINT 5.3)
```

Only touch your own folder. Need a change in someone else's contract? Edit section 4 of this file in a PR and tell them.

## 3. CLAUDE.md (copy this block into the repo root file)

```
# CLAUDE.md — offline multilingual lesson-video pipeline
HARD RULES
1. OFFLINE ONLY. Set HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1 at process start. Never call any
   external API, CDN, Google Fonts URL, or cloud TTS/translation. Runtime must work with Wi-Fi off.
2. DATA, NEVER CODE. The local LLM returns JSON matching LessonPlan.model_json_schema(). Never ask it
   for HTML/JS/SVG/Python/Manim. The renderer owns all drawing code.
3. PLAN IN ENGLISH ONLY. Indic text comes from IndicTrans2 (+ IndicProcessor) after validation.
4. AUDIO IS MASTER. TTS runs before rendering. Scene duration = measured audio length (tail pad
   0.35 s is already inside the audio; do not add it twice). Lesson total must be 30-90 s.
5. DETERMINISTIC RENDER. window.renderAtTime(t_sec) is a pure function of time. No setInterval,
   no unseeded Math.random, no Date.now inside the renderer.
6. Own folder only (see PLAN.md section 2). Contracts are in PLAN.md section 4.
7. After every merge run: pytest tests/test_e2e_offline.py
8. Keep code simple and readable. No new dependencies without telling the team.
```

## 4. Contracts (frozen after the lock; changes need team agreement)

**4.1 LessonPlan schema** — exactly `orchestrator/schema.py` from BLUEPRINT 1.2. Visual types: `flow, bullets, equation, labeled_diagram, graph, timeline, compare, title`. 4-6 scenes, narration 14-32 words (target 18-30) and spoken words only (no digits or symbols), 85-150 words per lesson, labels 1-6, steps 1-5. Optional `check {expr, result}` on the worked-example scene (pending CONTRACT CHANGE, see STATUS.md).

**4.2 Golden fixture** — `fixtures/golden_ohms_law.json` from BLUEPRINT 1.3.

**4.3 manifest.json** (written by localization, read by renderer + exporter)
```json
{
  "title": "...", "lang": "hi", "total_sec": 54.79,
  "audio": "lesson_audio.wav", "sample_rate": 24000,
  "scenes": [
    {"id": 1, "start_sec": 0.0, "end_sec": 9.92, "duration_sec": 9.92,
     "narration": "...(already translated)...",
     "visual": {"type": "title", "params": {"labels": ["..."], "steps": ["..."]}}}
  ]
}
```
Also write `golden_manifest_en.json` as soon as the first English TTS works so Farhan and Ayush stop waiting on Tarun.

**4.4 Renderer JS API** (Farhan)
- `window.initLesson(title, scenes, lang)` — `scenes` = manifest scenes. Preloads fonts, builds timeline, returns a Promise.
- `window.renderAtTime(t_sec)` — draws the frame for time t, synchronous.
- `window.totalDuration` — seconds.
- Browser playback mode (`player.html?topic=...&lang=...`): load manifest + audio, `requestAnimationFrame` loop that calls `renderAtTime(audio.currentTime)`. Audio is the clock.
- Fonts bundled locally via `@font-face` (Noto Sans, Noto Sans Devanagari, Noto Sans Kannada, Tamil, Telugu). Pick the family by `lang`. Zero network requests.
- Captions: bottom bar, current scene narration, word-by-word highlight using proportional timing across the scene duration. Auto-wrap and auto-shrink text so long Hindi/Kannada strings never overflow.

**4.5 Localization API** (Tarun)
- `OfflineIndicTranslator.localize_lesson(plan, lang) -> LessonPlan` (one batched call; formulas left untouched)
- `OfflineTTSEngine.synthesize_all_scenes(scenes, lang, out_wav) -> list[timing dicts]`
- `build_manifest(plan_localized, timings, lang) -> dict` (section 4.3)

**4.6 Orchestrator entry point** (Yyug)
- `generate_lesson(topic: str, lang: str, progress_cb=None) -> Path` returns the artifacts dir. Stages reported to `progress_cb(stage, pct)`: `plan, translate, tts, render, encode, done`. Returns instantly on cache hit.

**4.7 Web API** (Ayush)
- `POST /api/generate {topic, lang}` -> `{job_id}`; `GET /api/status/{job_id}` -> `{stage, pct, telemetry, error?}`; `GET /artifacts/{slug}_{lang}/lesson.mp4`; static `player.html`.
- UI: topic box, language selector (EN, HI, KN, TA, TE), progress bar by stage, in-page player, MP4 download button, error toast, per-stage timing shown (judges score speed).

## 5. Module specs and acceptance tests

**Yyug — orchestrator**
- Ollama call per BLUEPRINT 2.4: `format=LessonPlan.model_json_schema()`, `temperature=0`, `num_ctx=4096`, `num_predict=850`, `keep_alive=-1`, pass `think=False` for qwen3/gemma (wrap in try/except in case a model rejects the flag), static system prompt + 2 few-shot examples first so Ollama's prefix cache hits.
- Prompt: Hook -> Analogy -> Core rule -> Worked example -> Recap, Indian examples, spoken math spelled out in narration and symbols only in labels, labels/steps under 6 words.
- Few-shot overfitting guard: after the demo topics work, add a third few-shot from a non-physics domain (history/biology) so the model does not force every lesson into "V = I x R" style.
- Reliability ladder: schema-constrained call -> 1 retry with the validation error appended -> deterministic fallback template. The pipeline must never crash.
- Accept: 20 topics, >=19 valid plans without fallback, plan time < 15 s warm on the demo laptop.

**Tarun — localization**
- IndicTrans2 distilled 200M, `IndicProcessor` pre/post is mandatory, single batched call, Kannada output must contain U+0C80-0CFF and no Devanagari.
- Kokoro: `a` + `af_heart` for EN, `h` + `hf_alpha` (or `hm_omega`) for HI. Needs espeak-ng installed. Run a warm-up synthesis for every voice while online.
- MMS-TTS: `facebook/mms-tts-kan` (+ tam, tel). Check `tokenizer.is_uroman`; if True, uroman preprocessing is needed. `torch.manual_seed(42)` before each forward pass. Resample 16k -> 24k.
- Normalize loudness, add 0.35 s tail, write one master WAV and the manifest.
- Sanitize text for TTS: expand symbols/digits that VITS drops (`230` -> words in the target language, or keep digits only if audibly correct; test).
- Accept: HI and KN audio is audible, correct language, scene durations 4-15 s each, no clipping.

**Farhan — renderer**
- 8 templates, built in this order: title, bullets, compare, equation, flow, labeled_diagram, timeline, graph. Each takes `{labels, steps}` and animates in over ~0.6 s with easing, stays readable, then holds.
- Consistent theme (dark navy + one accent), large type (min 36 px labels, 30 px captions), no overflow with Kannada/Hindi lengths (test with real translated strings).
- Template choice mismatch (e.g. `graph` with non-numeric labels) must degrade gracefully to `bullets`, never throw.
- Accept: open `player.html` with the golden fixture + golden manifest, scrub `renderAtTime` from 0 to end, no errors, no layout overflow.

**Ayush — exporter / UI / tests**
- Playwright + FFmpeg `image2pipe` per BLUEPRINT (section 5.1 is missing from the blueprint file; the code in the second half of it is the exporter). 1280x720, 20 fps, `libx264 -preset ultrafast -crf 22 -pix_fmt yuv420p`, AAC audio, `+faststart`.
- Speed: if one export takes more than ~60 s, capture frames in 2-4 parallel pages and merge, or lower to 15 fps. Report per-stage seconds.
- `tests/test_e2e_offline.py` + `exporter/test_harness.py` (section 7).
- `README.md` with setup, architecture diagram and the licenses table.
- Accept: golden fixture exports a playable MP4 with synced audio, duration within +/-0.2 s of `total_sec`.

## 6. Timeline (today's date, now ~11:35)

| By | Milestone |
|---|---|
| 12:00 | Repo skeleton, `CLAUDE.md`, `schema.py`, golden fixture, this PLAN committed. Everyone has pulled and ran `ollama list`, `ffmpeg -version`, `python -m playwright install chromium`. |
| 14:00 (hard stop 15:00) | **English golden lesson plays in browser and exports MP4.** (Hardcoded JSON, no LLM.) |
| 18:00 | Live LLM planner, Hindi + Kannada, language selector, progress bar, cache. First full run: typed topic -> MP4 in HI and KN. |
| 22:00 | All 8 templates, caption highlight, error toasts, Tamil/Telugu if audio is good. Prompts tuned. |
| 22:00-05:30 | 20-topic stress test, fix worst failures, measure P50/P90 latency. **Sleep in shifts: two people sleep 3-4 h while two work, then swap.** |
| Freeze, 3-4 h before the final demo | No layout or prompt changes. Pre-cache 10 likely topics. Wi-Fi off, two full cold-start rehearsals. |

If you are behind at 15:00, cut scope in this order: Tamil/Telugu, graph + timeline templates, word-highlight captions, parallel frame capture. Never cut: English E2E, Hindi, Kannada, offline run.

## 7. Test harness (`exporter/test_harness.py`)

Run 20 topics (Photosynthesis, Newton's Third Law, Binary Search, Supply and Demand, DNA Replication, Pythagoras Theorem, Water Cycle, Compound Interest, Acid-Base Titration, TCP Handshake, plus 10 non-STEM: Indian Independence, Monsoon, GST, Mughal Empire, Democracy, etc.) x languages en, hi, kn. Assert:
1. Valid plan, 4-6 scenes, fallback used on <=1 of 20.
2. `total_sec` in [30, 90].
3. KN narration has Kannada characters and no Devanagari.
4. MP4 exists and is > 150 KB.
5. `ffprobe`: h264 yuv420p + aac, duration within +/-0.2 s of `total_sec`.
Write results to `reports/stress_<time>.csv` with per-stage seconds.

## 8. Known risks and fixes

- **Windows build pain:** `IndicTransToolkit` compiles Cython. Install "Build Tools for Visual Studio (C++)" tonight if `pip install IndicTransToolkit` fails. Test the import now, not at 17:00.
- **espeak-ng** must be installed for Kokoro Hindi (Windows MSI from the espeak-ng releases page) and be on PATH.
- **Kokoro package:** blueprint uses `kokoro` (PyTorch, `KPipeline`). If you installed `kokoro-onnx` (from the prep email), keep it and wrap it behind the same `synthesize_scene(text, lang)` signature. Don't run both.
- **Voices and models lazy-download.** Run one synthesis per voice and one translation per language while online, then set the offline flags.
- **Playwright Chromium** must be installed (`python -m playwright install chromium`) before Wi-Fi goes off.
- **`think` flag:** if a model errors on `think=False`, retry without it; prefer llama3.2:3b (non-thinking) as the default.
- **Translation drift:** IndicTrans2 can mangle numbers and units. Keep formulas out of translation (regex in `translator.py`) and check digits survive.
- **Kannada VITS drops symbols/numbers.** Test narration with digits early; expand numbers to words if needed.
- **Fallback ladder in demo:** LLM fails -> fallback template; IndicTrans2 fails -> pre-translated cached lesson; TTS fails for a language -> hide that language in the UI rather than crash.
- **Pre-translated cache:** for the 10 most likely judge topics, pre-generate all 3 languages so the first demo run is instant, but still keep live generation working (judges pick the topic).
- **Rules:** the organisers allowed Claude Code as a dev tool. The *running product* must not call any cloud AI. Keep the confirmation message/screenshot from the organisers.
- **Licenses:** MMS-TTS is CC-BY-NC (fine for the hackathon, list it). Llama 3.2 has its own community license. Put the table from BLUEPRINT 5.3 in the README.

## 9. Demo script (3 minutes)

1. Wi-Fi visibly off. Show the app cold-started.
2. Judge picks topic + language. Generate live; show stage timings.
3. Play in browser; point at synced captions and visuals.
4. Download MP4, open it.
5. Switch language on the same topic (plan cached, translate + TTS only) to show speed.
6. One slide of engineering: schema-constrained JSON, audio-master timing, deterministic renderer, offline stack + licenses.

## 10. Paste-ready kickoff prompts for Claude Code

**Everyone (first message):**
> Read CLAUDE.md, PLAN.md and BLUEPRINT.md fully. You are working on the `<FOLDER>` module only. Follow the contracts in PLAN.md section 4 exactly. Start by writing the acceptance test for your module, then implement, then run it. Do not call any network service. Ask me before changing a contract.

**Yyug (orchestrator):**
> Create orchestrator/schema.py from BLUEPRINT 1.2 and fixtures/golden_ohms_law.json from 1.3. Then implement prompts.py, planner.py (reliability ladder), fallbacks.py, cache.py and pipeline.py with `generate_lesson(topic, lang, progress_cb)`. Until localization and exporter exist, stub them with the golden fixture. Add a CLI: `python -m orchestrator.pipeline "Ohm's Law" hi`.

**Tarun (localization):**
> Implement localization/translator.py and tts_engine.py per PLAN.md 5 and BLUEPRINT 3.1-3.2, plus captions.py and build_manifest(). First milestone: golden_ohms_law.json -> English WAV + golden_manifest_en.json in 30 minutes. Then Hindi, then Kannada. Include a script that warms every voice/model and prints OK/FAIL per component.

**Farhan (renderer):**
> Build renderer/player.html, engine.js, templates.js per PLAN.md 4.4 and 5. Use fixtures/golden_ohms_law.json plus a hand-written manifest until golden_manifest_en.json exists. Templates in order: title, bullets, compare, equation, flow, labeled_diagram, timeline, graph. Bundle Noto fonts locally. Add a debug scrubber slider so I can drag time and see every frame.

**Ayush (exporter/UI):**
> Implement exporter/export_mp4.py (Playwright + FFmpeg image2pipe), exporter/app.py (FastAPI endpoints in PLAN.md 4.7 with a clean single-page UI), tests/test_e2e_offline.py and exporter/test_harness.py (PLAN.md section 7), run_demo.sh, README.md. First milestone: export the golden fixture to MP4 with audio.
