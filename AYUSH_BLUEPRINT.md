# AYUSH_BLUEPRINT.md — Backend API, MP4 Exporter, Tests, Run Scripts, README

You own **the engine room**: the FastAPI backend that connects the UI to the pipeline, the Playwright + FFmpeg exporter, the test and stress harness, the offline guarantees, and the README. This is "working end to end" (25%), "engineering" (15%) and "speed" (10%).
**The UI is not yours** (moved to Farhan). You provide a JSON API and static mounts only.
Read first: `CLAUDE.md`, `PLAN.md` (sections 3, 4.3, 4.6, 4.7, 7, 8), `BLUEPRINT.md` (exporter code near the end).

---

## 1. Files you own

```
exporter/
  export_mp4.py     frames -> MP4 (Playwright + FFmpeg)
  app.py            FastAPI app, job manager, static mounts
  check_env.py      one-command environment and offline readiness check
  test_harness.py   20-topic x 3-language stress run, writes reports/
tests/
  test_e2e_offline.py
run_demo.ps1        (Windows, primary)   run_demo.sh (bash, same logic)
requirements.txt    pinned working versions (update as the team adds packages)
README.md           setup, architecture, licenses table (BLUEPRINT 5.3), demo script
reports/            stress CSVs (gitignored)
```

## 2. Interfaces you depend on (stub them until they exist)

- Yyug: `orchestrator.pipeline.generate_lesson(topic, lang, progress_cb) -> Path` returns `cache/artifacts/{slug}_{lang}/` containing `manifest.json`, `lesson_audio.wav` and (after you export) `lesson.mp4`. Also `orchestrator.pipeline.warmup()` loads all models once and `available_languages()`.
- **Division of work:** the pipeline calls *your* `export_mp4.render_and_mux_mp4(...)` as its last stage (`render` + `encode`). Until Yyug has wired it, your own CLI calls it directly.
- Farhan: `renderer/player.html` with `window.initLesson(title, scenes, lang)`, `window.renderAtTime(t)`, `window.totalDuration`, and `window.ready = true` once loaded.
- Stubs for day one: copy `fixtures/golden_manifest_en.json` (Farhan/Tarun create it) and a 1 s sine WAV generated with numpy into a fake artifacts dir so you can export before anyone else is done.

## 3. Exporter (`exporter/export_mp4.py`)

Start with the version in BLUEPRINT (Playwright `page.screenshot` -> FFmpeg `image2pipe`). Signature:
```python
render_and_mux_mp4(artifact_dir: Path, lang: str, progress_cb=None, fps=20) -> Path
```
It reads `manifest.json` + `lesson_audio.wav` from `artifact_dir`, opens `renderer/player.html` via `file://` or the local server, calls `initLesson(manifest.title, manifest.scenes, lang)`, waits for `window.ready`, loops frames `t = i / fps`, writes `lesson.mp4`.

Rules:
- 1280x720, `libx264 -preset ultrafast -crf 22 -pix_fmt yuv420p`, AAC 128k, `-movflags +faststart`. Total frames = `ceil(total_sec * fps)`; do not use `-shortest` to mask mismatches, verify instead.
- `await document.fonts.ready` before the first frame (Farhan's `initLesson` does it; double-check).
- **Network audit:** register `page.on("request", ...)`; any URL that is not `file://`, `data:`, `blob:` or `http://127.0.0.1` / `localhost` is recorded and the export **fails loudly** in test mode. This proves the offline claim.
- Progress: call `progress_cb("render", pct)` during capture, `progress_cb("encode", pct)` when closing ffmpeg.
- If ffmpeg dies, raise with its stderr tail; never leave a zero-byte `lesson.mp4`.
- Chromium args: `--disable-gpu-vsync --font-render-hinting=none --force-color-profile=srgb`.

### Speed (10% of the score, and the demo is live)
Target: a 55 s lesson exports in under 60 s; stretch goal under 30 s. Do these in order, measuring each:
1. **Faster capture than screenshot:** call `page.evaluate("document.getElementById('stage').toDataURL('image/jpeg', 0.9)")` and base64-decode it. It skips the compositor and is often 2-3x faster. Keep screenshots as fallback.
2. **Lower cost per frame:** 20 fps (or 15 fps for lessons > 75 s), `quality 85-90`.
3. **Parallel capture:** use the async Playwright API with 3-4 pages in one browser; each page renders a contiguous frame range into a list of JPEG bytes; the main task writes ranges to ffmpeg's stdin in order. Memory is fine (about 1,100 frames x 80 KB).
4. **Skip the browser for static frames:** hold frames (when nothing animates for > 0.5 s) can be reused: hash the canvas bytes of the previous frame and reuse. Optional.
5. Log per-stage seconds to the job record; Farhan's UI shows them.

## 4. Backend (`exporter/app.py`)

FastAPI + uvicorn, single process, **one worker** (GPU and models are shared). Serve on `127.0.0.1:8000`.

Endpoints (frozen, PLAN 4.7):
| Method | Path | Behaviour |
|---|---|---|
| POST | `/api/generate` | body `{topic, lang}`; validate (topic 2-120 chars, lang in available); create job; run `generate_lesson` in a background thread; return `{job_id}`. If `(slug, lang)` artifacts exist, mark done immediately (cache hit). |
| GET | `/api/status/{job_id}` | `{job_id, topic, lang, stage, pct, stage_times, telemetry, error, mp4_url, manifest_url, audio_url, cached}` |
| GET | `/api/languages` | languages that actually work on this machine (from `pipeline.available_languages()`), e.g. `["en","hi","kn"]` |
| GET | `/api/examples` | list of pre-cached example topics with the languages already cached |
| GET | `/api/health` | `{ollama, ffmpeg, chromium, models_loaded, offline_flags}` for the UI badge and your tests |
| static | `/` | redirects to `/web/index.html` |
| static | `/web`, `/renderer`, `/artifacts` | mounts of `web/`, `renderer/`, `cache/artifacts/` |

Job manager details:
- In-memory dict of jobs; a global lock/queue so only one generation runs at a time (second request waits and shows `queued`).
- `progress_cb(stage, pct)` updates `stage`, `pct` and records `stage_times[stage]` when the stage changes. Stages: `queued, plan, translate, tts, render, encode, done, error`.
- Errors: catch everything, store a short human message plus the traceback in the server log (never send the traceback to the browser).
- Topic slug: lowercase, ascii-fold, non-alphanumerics -> `_`. Keep identical to Yyug's `cache.py` (import his function, do not re-implement).
- Startup event calls `pipeline.warmup()` in a thread and flips `models_loaded`.
- Environment at process start (top of `app.py` before any import of torch/transformers):
  ```python
  import os
  os.environ.setdefault("HF_HUB_OFFLINE", "1")
  os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
  ```
- CORS: not needed (same origin). Disable docs UI if you like (`docs_url=None`), it is irrelevant.

## 5. `check_env.py` (run it before everything, and before the demo)

Prints a green/red table; exit code 1 if anything required is red.
- Python version and key imports: `ollama, fastapi, uvicorn, playwright, pydantic, torch, transformers, IndicTransToolkit, kokoro, soundfile, scipy, numpy`.
- `ffmpeg -version`, `ffprobe -version` on PATH.
- Playwright Chromium installed (launch it headless and open `about:blank`).
- Ollama reachable at `http://127.0.0.1:11434` and the configured `OLLAMA_MODEL` is in `ollama list`.
- Local files exist: IndicTrans2 checkpoint dir/cache, `mms-tts-kan` (+tam/tel), Kokoro weights and voices (`af_heart`, `hf_alpha`), Noto fonts in `renderer/assets/fonts`.
- `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` set.
- **Real offline test:** try `socket.create_connection(("1.1.1.1", 53), timeout=2)`; in offline mode it must fail (warn if the Wi-Fi is still on, informational before the demo, required on demo day).
- GPU info (`nvidia-smi` query) and free VRAM; warn below 3 GB free.

## 6. Tests

### `tests/test_e2e_offline.py` (run after every merge)
1. Block outbound network inside the test process: monkeypatch `socket.socket.connect` to raise for any host not in `127.0.0.1/::1/localhost`.
2. With the golden manifest and WAV in a temp artifacts dir, call `render_and_mux_mp4` and assert: file exists and > 150 KB; `ffprobe` shows `h264` + `yuv420p` + `aac`; video duration within +/-0.2 s of `manifest.total_sec`; zero non-local requests recorded by the exporter's network audit.
3. API test with FastAPI `TestClient`: `POST /api/generate` for the golden topic in en (stubbed pipeline) -> poll status -> `done` with `mp4_url`; `GET` of the MP4 returns 200; `/api/languages` and `/api/health` respond.
4. Marked `@pytest.mark.slow`: full real pipeline for "Ohm's Law" in en, hi, kn.

### `exporter/test_harness.py` (overnight stress)
Topics: the 10 from PLAN 7 plus 10 non-STEM (Indian Independence, Monsoon, GST, Mughal Empire, Democracy, Photosynthesis in Plants, Fractions, Human Heart, Climate Change, Sound Waves). Languages: en, hi, kn (add ta, te if enabled). For each pair run the real `generate_lesson`, then check:
1. Plan valid and `fallback_used == False` on at least 19 of 20 topics (record which fell back).
2. `total_sec` in [30, 90].
3. KN narration has chars in U+0C80-0CFF and none in U+0900-097F; HI has U+0900-097F.
4. MP4 > 150 KB; `ffprobe` h264 yuv420p + aac; duration within +/-0.2 s.
5. No non-local request recorded.
6. Save the **last frame and the 50% frame** of every video as PNG into `reports/frames/{slug}_{lang}_{t}.png` so Farhan can eyeball layout problems quickly.
Write `reports/stress_<timestamp>.csv` with columns: topic, lang, ok, fallback, total_sec, plan_s, translate_s, tts_s, render_s, encode_s, total_gen_s, mp4_kb, notes. Print P50/P90 of `total_gen_s` per language at the end (the number for the pitch: "median X seconds").

## 7. Run scripts

`run_demo.ps1` (Windows, primary):
```powershell
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:OLLAMA_MODEL = "qwen2.5:3b"
$env:PYTHONUTF8 = "1"
python exporter/check_env.py
if ($LASTEXITCODE -ne 0) { Write-Host "Environment check failed"; exit 1 }
Start-Process "http://127.0.0.1:8000"
python -m uvicorn exporter.app:app --host 127.0.0.1 --port 8000
```
`run_demo.sh` is the same for bash. Also add `scripts/precache.py` that generates the 10 example topics in all languages (so the first demo clicks are instant) and `scripts/clean_cache.py`.

## 8. README.md (also scored under engineering)

Sections: what it is (1 paragraph), architecture diagram (ASCII or Mermaid), models and license table (BLUEPRINT 5.3), how to run offline (`check_env`, `run_demo`), design decisions (audio-master timing, deterministic renderer, schema-constrained JSON from the LLM, English-only planning + IndicTrans2, single batched translation, caching), measured performance (paste your P50/P90 from the harness), known limits, team. Keep it honest: list what is not done.

## 9. Timeline for you

| By | Deliverable |
|---|---|
| 12:30 | `requirements.txt`, `check_env.py` (even partial), and `export_mp4.py` exporting the golden manifest + fake WAV to a playable MP4 (needs Farhan's first `player.html`; until then draw a test pattern in a throwaway page to prove the FFmpeg path). |
| 14:00 | `app.py` with all endpoints against a stubbed pipeline; `test_e2e_offline.py` green; speed measured (frames/s). |
| 18:00 | Wired to Yyug's real `generate_lesson`; queueing, cache hits, error messages; parallel capture implemented. |
| 22:00 | `test_harness.py` complete; `precache.py`; `run_demo.ps1`; README draft with licenses. |
| Overnight | Run the stress harness every time the team merges something big; send Farhan the failing frames and Yyug the fallback topics; track P50/P90. |
| Freeze | Final `check_env` on the demo laptop with Wi-Fi off, two full rehearsals timed with a stopwatch. |

## 10. Acceptance

- Golden manifest exports in < 60 s to a playable MP4 with audio in sync (play it in VLC and in Chrome).
- `POST /api/generate` -> status polling -> MP4 URL works end to end with the real pipeline in en, hi, kn.
- `pytest tests/test_e2e_offline.py` green with the network blocked.
- Harness: >= 19/20 non-fallback plans, all durations in range, zero network requests, P50 generation time recorded.
- `check_env.py` clean on the demo laptop.

## 11. Paste-ready Claude Code prompt

> Read CLAUDE.md, PLAN.md, AYUSH_BLUEPRINT.md and BLUEPRINT.md (exporter code). You own exporter/, tests/, run_demo.ps1/.sh, requirements.txt, README.md, scripts/. You do NOT own the UI (Farhan owns web/). First: write exporter/check_env.py and exporter/export_mp4.py (signature `render_and_mux_mp4(artifact_dir, lang, progress_cb=None, fps=20)`, with the network audit and a toDataURL capture path), and prove it on a fake artifact (golden manifest + generated sine WAV). Then exporter/app.py with the endpoints in AYUSH_BLUEPRINT section 4 against a stubbed pipeline, then tests/test_e2e_offline.py with outbound network blocked. Commit small and often on branch ayush/backend and push. Do not touch other folders.
