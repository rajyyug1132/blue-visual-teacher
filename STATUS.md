# STATUS.md

Read this first (AGENTS.md [MILESTONES]). Each owner updates their own row last.

## DONE checks D1-D10

Run `python -m orchestrator.done_checks` (add `--skip-slow` to skip the live 20-topic and 60-video runs).
Evidence per check in `logs/D#.log`; latest table in `logs/summary.md`.

| D# | check | state | owner | evidence |
|---|---|---|---|---|
| D1 | schema + golden fixture (CC-1 counts [22,27,24,29,21]) | PASS | YYUG | logs/D1.log |
| D2 | planner ladder, 20 topics >=19 valid, P50 <20 s | PASS: 19/20 valid, P50 15.1 s, 0 final failures, 0 unspoken answers | YYUG | logs/D2.log |
| D3 | tier-1 plan hit <5 ms, tier-2 artifact hit serves MP4 | PASS | YYUG | logs/D3.log |
| D4 | IndicTrans2 batched + IndicProcessor, KN no Devanagari | PASS (pure-Python IndicTransToolkit in .venv) | TARUN | logs/D4.log |
| D5 | Kokoro EN/HI, MMS KN seed 42, 24 kHz, 0.35 s tail, deterministic | PASS | TARUN | logs/D5.log |
| D6 | renderer: 8 templates, deterministic, Indic fits 1280x720 | PASS | FARHAN (assist PR #2) | logs/D6.log |
| D7 | export 20 topics x en/hi/kn, BLUEPRINT 6.2 checks | PASS 60/60 (checked against the tier-2 cached MP4s from 15:04-15:48; not re-rendered after the v1 merge) | AYUSH (assist PR #4) | logs/D7.log |
| D8 | UI: language selector, progress, toasts, MP4 download | PASS | FARHAN + AYUSH | logs/D8.log |
| D9 | pytest tests/ incl. test_e2e_offline.py, sockets blocked | PASS: 192 passed, 3 skipped (30.6 min) | ALL | logs/D9.log |
| D10 | README licenses, run_demo.sh, 10 topics pre-cached | PASS | AYUSH (assist PR #4) | logs/D10.log |

Full rerun on branch v1 (yyug/integration + tarun/localization), 2026-10-27 19:22-20:20: **10/10 PASS** (logs/summary.md).

Runtime for these checks: Python 3.11 venv with requirements.txt (transformers 4.46.3, CPU torch), IndicTransToolkit
built pure-Python (no MSVC here), HF weights in the standard cache. See LEARNINGS.md.

## Milestones

| Owner | Module | State | Last check | Next |
|---|---|---|---|---|
| YYUG | orchestrator/ | Planner + plan cache + fallback + math guard + spoken-words repair + post-TTS duration gate. Era-marked dates (BCE/BC/CE/AD) allowed on policy-none. | 2026-10-27 · D1 PASS · D2 PASS 19/20 P50 15.6 s · D3 FAIL (Playwright Chromium missing) · numeric_guard+orchestrator 127 passed | Install Playwright Chromium so D3/D7/D8/D9 can export. |
| FARHAN | renderer/ web/ | ALL GREEN F1–F10 (farhan/ui): deterministic engine, 8 templates, fitText, captions, web UI with stepper, toast, download, ?mock=1 | logs/f1_f10.log, logs/f1_f10_report.json | Merged into v1 |
| TARUN | localization/ | Done (All 5 punch list items resolved: Native listen log, voice cache audit & hf_alpha rating, anti-silent-tone guard, speech rate benchmark, model licenses) | 183 unit tests green + 5 real neural tests green (D4/D5) | Ready for v1 merge |
| AYUSH | exporter/ | — | — | — |

### Planner bench (5 topics, uncached, RTX 3050 6 GB)

| model | valid | math_ok (own check right) | checks fixed | qualitative template | P50 plan s | VRAM |
|---|---|---|---|---|---|---|
| qwen2.5:3b | 4/5 | 0 | 2 | 0 | 8.0 | 2.2 GB, 100% GPU |
| llama3.2:3b | 5/5 | 0 | 0 | 2 | 9.1 | 2.6 GB, 100% GPU |
| qwen2.5:7b | 5/5 | 0 | 1 | 0 | 20.4 | 5.2 GB, 18% on CPU |

No model got its own worked-example arithmetic right; the guard corrects it. Invented quantities seen live:
qwen2.5:3b Monsoon ("V = Rain / (A × T)" pseudo-formula), llama3.2:3b Monsoon ("fifty-five degrees Celsius").

## Handoffs

- YYUG -> TARUN · localization/translator.py · add `"bn": "ben_Beng"` to LANG_CODE_MAP on tarun/localization (already patched on v1) · Bengali replaced Telugu everywhere except this map, so IndicTrans2 got the raw tag `bn` and test_multilingual_sync failed with "Invalid target language tag: bn" whenever the real model is loaded · blocking? n (fixed on v1)

- TARUN -> FARHAN, AYUSH · localization/tts_engine.py · Added friendly voice identifiers "enm" (Michael, Male Professor) and "enf" (Sarah, Female Educator) for English Kokoro TTS, selectable via voice="enm"|"enf" in TTS calls and test_voice CLI; web UI / API can expose these as user options · blocking: n
- TARUN -> FARHAN · `fixtures/golden_manifest_en.json` · English audio timing manifest delivered (54.79s total) · unblocks renderer `initLesson` & audio clock · blocking: n
- TARUN -> AYUSH · `fixtures/golden_manifest_en.json` · English audio timing manifest delivered · unblocks Playwright + FFmpeg export testing · blocking: n
- TARUN -> YYUG · `orchestrator/schema.py` · Recommend allowing non-English plans to bypass the word minimum (handled in `translator.py` via `ensure_word_budget`) · blocking: n

- YYUG -> TARUN · localization/tts_engine.py, translator.py · Kokoro, IndicTrans2 and MMS-TTS run on CPU (fp32): take the device from `orchestrator.device.get_device()` (default now `cpu`, env DEVICE=cpu|cuda), never hardcode "cuda"; load once at startup · the planner is now qwen2.5:7b and needs the whole GPU · blocking? n (y before the 18:00 HI+KN milestone)
- YYUG -> TARUN · localization/ · please report CPU timings for one 5-scene lesson (translate + TTS) per language; if total > ~30 s, batch IndicTrans2 once and run scene TTS in a ThreadPoolExecutor (BLUEPRINT 3.2) · speed is 10 % of the score and the planner already takes ~20 s · blocking? n
- (superseded) YYUG -> TARUN · installed torch is `2.13.0+cpu` · fine now that localization runs on CPU; only needed if we go back to DEVICE=cuda
- YYUG -> TARUN · localization/translator.py · `SceneSpec.check` (expr/result) is new and optional; do NOT translate it, leave it as-is · keeps math intact · blocking? n
- YYUG -> FARHAN, AYUSH · fixtures/golden_ohms_law.json · scene 4 narration now reads "two hundred thirty volt ... forty-six ohms ... five amperes" (29 words); stub total moves 54.79 s -> 55.23 s; labels/steps unchanged · fixture had digits, which the spoken-words rule now rejects · blocking? n
- YYUG -> FARHAN · renderer · ignore the optional `check` key on scenes; never render it · it is planner metadata · blocking? n
- YYUG -> TARUN · localization/tts_engine.py · run `orchestrator.spoken.speak_forms(text)` on every string right before TTS (NFKC + CO2 -> carbon dioxide, km² -> square kilometres) · safety net if IndicTrans2 reintroduces digits/formulas · blocking? n
- YYUG -> AYUSH · README.md "Known limits" · add: "Descriptive topics (history, geography, processes) carry no numbers: the planner blocks digits, number words above ten, units and formulas there. Numeric worked examples are arithmetic-checked, but formulas outside a verified bank are not asserted as fact." · judges score honest limits over hidden bugs · blocking? n
- TARUN -> YYUG, AYUSH, FARHAN · localization/tts_engine.py · Voice pack audit: Kokoro offline cache contains ONLY hf_alpha.pt (Indian female), hm_omega.pt (Indian male), and af_sarah.pt. am_michael, enim, and enif are NOT cached as standalone files. Defaulting to hf_alpha (Indian-accented female educator) runs 100% offline with zero synthetic tone fallback. Silent tone fallback removed; failures now raise RuntimeError and log loudly. · blocking? n

## CONTRACT CHANGE proposals

### CC-1 · LessonPlan: spoken-words narration + optional worked-example check · proposed by YYUG · status: OPEN (needs FARHAN, TARUN, AYUSH)

**What changes in `orchestrator/schema.py`**

1. `SceneSpec.narration`: 14-32 words (was 8-42), max 320 chars (was 240), and spoken words only: no digits or
   symbols (`0-9 = × ÷ + / % Ω < > ° √ π`), checked after Unicode NFKC so `CO₂` and `km²` count as digits.
   Numbers are written in words ("two hundred thirty"); figures and formulas stay in `visual.params.labels/steps`.
2. `LessonPlan` model validator: 85-150 narration words per lesson and an estimated 35-85 s of audio
   (words / 2.3 + 0.35 s per scene).
3. New optional field `SceneSpec.check: Optional[Check] = None`, `Check{expr: str (<=60 chars), result: str (<=30 chars)}`.
   Only the worked-example scene carries it, e.g. `{"expr": "230 / 46", "result": "5"}`.
4. `fixtures/golden_ohms_law.json` scene 4 narration rewritten in words (see Handoffs). No other fixture change;
   the fixture has no `check`.

**Why**

- TTS reads digits and symbols badly (Kokoro/MMS drop or mangle "230 V", "Ω", "%"), and IndicTrans2 mistranslates numbers.
  Spelled-out numbers translate and speak correctly in EN, HI and KN.
- The 3B planner gets worked-example arithmetic wrong (live: compound interest 425 vs 162.89, 2718.13 vs 1645.31).
  `check` lets the orchestrator verify it (AST whitelist, never eval) and replace the wrong number before TTS.
  Teaching quality is 20 % of the score.

**Compatibility**

- `check` defaults to None: existing JSON (including the fixture) validates unchanged; renderer and exporter can ignore it.
- `timing_manifest`, `window.initLesson/renderAtTime` and the manifest format are unchanged.
- Narration strings are shorter-or-equal and contain no digits: caption layout only gets easier.
- Tighter word bounds only reject plans that would have run outside 35-85 s of audio anyway.

**Asks**

- FARHAN: confirm the renderer ignores unknown scene keys (`check`).
- TARUN: confirm `localize_lesson()` copies `check` untouched; confirm spelled-out numbers sound right in HI/KN.
- AYUSH: update any test that hardcodes 54.79 s for the golden fixture to 55.23 s.

Votes: YYUG ✅ · FARHAN ☐ · TARUN ☐ · AYUSH ☐
