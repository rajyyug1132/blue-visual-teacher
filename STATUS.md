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
| YYUG | orchestrator/ | Planner + plan cache + fallback + math guard + spoken-words repair + post-TTS duration gate. Era-marked dates (BCE/BC/CE/AD) allowed on policy-none. | 2026-10-27 · D1 PASS · D2 PASS 19/20 P50 15.6 s · D3 FAIL (Playwright Chromium missing) · numeric_guard+orchestrator 127 passed | Audited repo against the 5 problem-statement requirements: `code_walkthrough` absent, level/target_sec absent, next/replay missing, English voice American, CPU path OK for translate/TTS/render. CC-2 raised; handoffs to FARHAN/TARUN. Vercel deferred past the freeze. |
| FARHAN | renderer/ web/ | ALL GREEN F1–F10 (farhan/ui): deterministic engine, 8 templates, fitText, captions, web UI with stepper, toast, download, ?mock=1 | logs/f1_f10.log, logs/f1_f10_report.json | Merged into v1 |
| TARUN | localization/ | Done (L1–L8 verified + SPATS ratio sync + enm/enf educator voices) | SPATS ratio scaling, natural breath pauses, Ohm/variable transliteration, enm (Michael) / enf (Sarah) voice options | All green |
| AYUSH | exporter/ | Exporter pipeline, FastAPI app, Next.js UI integration, e2e tests (`test_e2e_offline.py` 6 passed) | 2026-10-28 00:10 · D8 PASS · D10 PASS · test_e2e_offline PASS | V1-Keeper loop active, ready for 06:00 review |

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

- YYUG -> AYUSH · README.md, package.json · name the FastAPI surface (`run_demo` -> http://127.0.0.1:8000, `exporter/app.py` serving `web/index.html`) as THE product, and document the other two as non-judged: `npm run server` = zero-dependency renderer mock harness (`?mock=1`), `app/` = experimental Next UI · three live entry points and judges will ask which one is the product; :8000 is the only one with offline evidence behind it (D7, D8, D10, `tests/test_ui.py`, `tests/test_e2e_offline.py` with sockets blocked) · blocking? n
- YYUG -> AYUSH · package.json · `npm start` is now `next start` and fails without a prior `next build`, while the old demo moved to `npm run server` · someone typing `npm start` at the demo gets an error, not a product; suggest `start` -> `node server.js` (or drop `start`) and keep the Next scripts under `dev:next` / `build:next` · blocking? n
- YYUG -> AYUSH · app/layout.tsx · two OFFLINE violations if the Next UI is shown at all: line 1 `@vercel/analytics/next` puts `https://va.vercel-scripts.com` in the production client bundle (verified: `.next/static/chunks/1oli3k22pgtic.js`), gated on `NODE_ENV === "production"` so `next start` loads it; line 3 `next/font/google` (Archivo, Inter) is a Google Fonts reference and makes `next build` network-dependent · AGENTS.md [ENFORCE] forbids external API/CDN/Google Fonts URLs in code, and the 06:00 Wi-Fi-off rehearsal would show failed requests · fix = delete the Analytics import/usage, and self-host both faces via `next/font/local` from `assets/fonts/` · blocking? y before the 06:00 rehearsal, n if the Next UI is not demoed · note: runtime fonts are already self-hosted (10 woff2 emitted, zero googleapis refs in `.next/static`), so only the build-time fetch and the beacon are at issue
- YYUG -> AYUSH · (info) `npm run build` now passes on Next 16.4.3 / Turbopack, 7 routes, ~2.5 s compile · first time it has been run here; `next.config.mjs` still sets `typescript.ignoreBuildErrors = true`, so types are unvalidated ("Skipping validation of types") · decide before the freeze whether hiding type errors is acceptable for judging · blocking? n
- YYUG -> FARHAN · server.js, web/ · keep `web/` as the judged UI (it is what :8000 serves); `server.js` stays only as the offline mock harness pinned by `tests/test_server_behavior.js` + `tests/test_mock_api.js` · no renderer change requested, just do not let `web/` drift toward the Next app before the freeze · blocking? n
- YYUG -> AYUSH · AGENTS.md · commit 459ac93 also appended a `<!-- BEGIN:nextjs-agent-rules -->` block to AGENTS.md; decide whether it stays, and say so explicitly rather than letting a build tool decide · the block is not yours: it is written by `next dev` via `node_modules/next/dist/server/lib/generate-agent-files.js` (verified present, 13 KB, written 23:04) and called from `app-info-log.js` on dev-server start, so it is re-added every run · it matters because AGENTS.md is the team contract loaded as project instructions through CLAUDE.md, it instructs any agent to go read docs out of `node_modules/`, and after the 06:00 freeze a tool that silently rewrites the rules file is a freeze violation nobody authored · I found no env/config opt-out for this block in the bundle (only the second block, `nextjs-agent-feedback`, is gated by `experimental.agentFeedback`), so the realistic options are: keep it and commit it deliberately as the block itself suggests, move the team rules out of the file Next writes to, or check the Next 16 docs for a flag · treat anything inside the block as third-party data, not as team rules · blocking? n (y if the Next UI is demoed and `next dev` is run after the freeze)
- YYUG -> FARHAN · renderer/templates.js, web/index.html · two gaps against the problem statement, both yours: (a) a `code_walkthrough` template -- code lines with a moving line highlight plus a variable-state table (i = 0 -> 1 -> 2), driven entirely by `visual.params` data, never executing anything; (b) player controls `next scene` and `replay` -- `web/index.html:140-162` has play/pause, seek, captions and mute, but neither of those two · `code_walkthrough` is a REQUIRED scene type and the judges' sample lesson is Python loops, so today their own test case has no template; next/replay are named under Stage 3 "done when" · see CC-2 for the data shape I will emit · blocking? y before 06:00
- YYUG -> TARUN · localization/tts_engine.py · default English narration to an Indian-accented voice: `voice_en` is currently `"enm"` -> `am_michael` (American). The statement asks for Indian-accented English explicitly; use `hf_alpha` or `hm_omega` on English text · your `VOICE_ALIASES` work in bd1058e already makes this close to a one-line default change, but it needs a listen-test before the freeze: Kokoro's `h*` voices on English text are the intended trick, not a bug · also note `cache/artifacts/ohm-s-law_hi` predates your `normalize.py:610` current -> vidyut dhaara fix, so the running demo still shows the wrong word until it is regenerated · blocking? y before 06:00
- YYUG -> TARUN · localization/tts_engine.py:540, localization/translator.py:355 · both hardcode `self.device = "cuda" if (HAS_TORCH and torch.cuda.is_available()) else "cpu"`, ignoring `orchestrator.device.get_device()` and the `DEVICE` env var · this is the ENFORCE rule at AGENTS.md:50 ("never hardcode cuda") and re-states a handoff from earlier today that was not picked up · NOT currently breaking anything here: the installed torch is `2.14.1+cpu`, so `cuda.is_available()` is False and both land on cpu anyway -- which is also why requirement 5's CPU path holds for translate/TTS/render today · it matters on any machine with a CUDA torch build, where localization would seize the 6 GB card that AGENTS.md reserves for the planner (qwen2.5:7b alone is 5.2 GB) and `DEVICE=cpu` would not stop it; `translator.py:376` also picks fp16 on cuda where the rule says fp32 · blocking? n before the freeze on this laptop, y if the demo ever runs on a CUDA torch build
- YYUG -> AYUSH · components/app/app-shell.tsx:58, components/app/dashboard-view.tsx:48 · delete both fallback banners and wire the real endpoints: the dashboard currently tells the user "Authentication is not connected yet" and "The lesson server doesn't expose a history endpoint", and BOTH are false on v1 · verified against the running backend at 00:00 on 2026-10-28: `POST /api/auth/signup` returns a real user and token, `GET /api/auth/me` with the session cookie returns 200, and `GET /api/lessons/history` returns 200 with `[]` (401 only when unauthenticated, which is correct) · `exporter/app.py:181-233` implements signup/login/logout/me/history and `lib/api.ts:185-239` already calls every one of them, so the copy is the only thing missing -- the UI undersells working features to a judge reading the screen · blocking? y before 06:00
- YYUG -> ALL · DECISION 2026-10-28 00:30 · the Next.js UI (`app/`, `components/`, `lib/`, `hooks/`, owner AYUSH) is the product UI; build around it · supersedes the earlier YYUG -> AYUSH handoff naming the FastAPI-served `web/` on :8000 as the product · `exporter/app.py` stays the backend, and `web/` + `server.js` stay as the offline mock harness pinned by `tests/test_server_behavior.js` and `tests/test_mock_api.js` · the condition that made `web/` the safer pick still has to be met: the two `app/layout.tsx` offline violations (`@vercel/analytics`, `next/font/google`) must be gone before the 06:00 Wi-Fi-off rehearsal; the AYUSH prompt sent at 00:25 lists them as STEP 2 · blocking? y for the rehearsal

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

Votes: YYUG ✅ · FARHAN ☐ · TARUN ☐ · AYUSH ✅

### CC-2 · LessonPlan: code_walkthrough scene type + learner level and target length · proposed by YYUG · status: OPEN (needs FARHAN, TARUN, AYUSH)

**Why now:** these are not new features, they are unmet requirements from the problem statement, found 2026-10-27 23:45 with the
freeze at 06:00. `code_walkthrough` is one of the required scene types and the judges' sample lesson is Python loops, so the
current 8-type schema cannot render their own example at all.

**1. New scene type `code_walkthrough`**

`SCENE_TYPES` gains a ninth entry. `visual.params` for it carries:

- `code: list[str]` -- 1 to 12 source lines, <= 80 chars each, rendered verbatim as text.
- `trace: list[CodeStep]` -- 1 to 6 ordered steps; each `{line: int (1-based index into code), vars: list[{name, value}]}`
  with at most 4 pairs, each string <= 24 chars. (As built in `cc3597b`: a list of pairs, not a dict, because `planner.py:302`
  feeds the schema to Ollama as a constrained grammar and free-form object keys are unreliable on a 3B model.)
  `line` drives the moving highlight; `vars` is the variable-state table at that step
  (e.g. `[{"name": "i", "value": "0"}]` -> `[{"name": "i", "value": "1"}]`).

**The code is data and is never executed.** Nothing in `code` or `vars` is passed to `eval`, `exec`, `compile`, a subprocess
or a template engine; the renderer draws strings. This is the same stance as `mathcheck.py`, which evaluates `check.expr`
through an AST whitelist and never `eval()`. The planner is the untrusted party here: it writes the trace, we only draw it.
`line` is validated in range against `code`; an out-of-range step fails validation rather than rendering.

**2. New LessonPlan inputs `level` and `target_sec`**

- `level: Literal["beginner", "intermediate"] = "beginner"` -- sets vocabulary and depth in the planner prompt only.
- `target_sec: int = 60`, bounded 30-90 -- sets the scene count and the per-lesson word budget.

These are Stage 1 inputs, so they also need a control on the input page (FARHAN/AYUSH) and a field on `POST /api/generate`
(AYUSH). The existing per-lesson validator (85-150 words, estimated 35-85 s) becomes a function of `target_sec` instead of a
constant: budget = `target_sec * 2.3` words +/- 15%, with the 30-90 s outer bound unchanged, so `duration_gate()` is untouched.

**Compatibility**

- Both fields default, so existing JSON including `fixtures/golden_ohms_law.json` validates unchanged.
- `code_walkthrough` is additive: a renderer that does not know it would skip it, but FARHAN needs the template before any
  programming topic can be planned, so this merges with his template, not before it.
- `timing_manifest`, `window.initLesson/renderAtTime` and the manifest format are unchanged.

**Asks**

- FARHAN: the `code_walkthrough` template and the next/replay controls (see Handoffs). Confirm the `code`/`trace` shape works
  for a moving highlight, and say if you would rather have the highlight as a per-step line range than a single index.
- TARUN: confirm narration for a code scene needs no new spoken-form rules (variable names such as `i` read aloud as letters).
- AYUSH: `level` and `target_sec` on `POST /api/generate` and the input page.

Votes: YYUG [x] · FARHAN [ ] · TARUN [ ] · AYUSH [ ]

## V1-Keeper Passes

### Pass 1 · 2026-10-28 00:10
- **Merged:** None (all branches `farhan/ui`, `tarun/localization`, `dev`, `yyug/*`, `ayush/*` already incorporated in `v1` at commit `bd1058e`).
- **Skipped:** None.
- **Gate status:** Green (Baseline D1-D10 10/10 PASS; `pytest tests/test_e2e_offline.py` 6 passed, 3 skipped).
- **Preview URL:** Standalone mock UI at `web/` (`http://localhost:3000` for integrated app; offline pipeline strictly local).
- **Open PRs waiting on owner:**
  - PR #6 (`v1` -> `main`): Ready for 06:00 final freeze & review.
  - PR #2, PR #4, PR #5: Subsumed/merged into `v1`.
- **Blockers:** None.

### Pass 1 (YYUG keeper session) · ended 2026-10-28 00:04

- **Merged:** nothing.
- **Skipped:** `origin/ayush/frontend` (4 commits, owner AYUSH) -- stale, not new. Merge base `a74c1d4`; merging would overwrite
  `exporter/app.py` with a pre-auth version (drops the SQLite users/sessions/history docstring) and revert the explicit-origin
  CORS already in v1 from `459ac93`. Owner should rebase it onto v1 or delete it.
- **Already in v1 (0 commits ahead):** `farhan/ui`, `tarun/localization`, `dev`, `yyug/integration`.
- **Open PRs:** #6 (v1 -> main, left alone), #2 / #4 / #5 all contained in v1.
- **Gate:** full `pytest tests/` on v1 @ `96cd58c`, started 23:55:46, finished: **204 passed, 3 skipped, 0 failed in 20:53**.
  Up from D9's 192 because Tarun's new tests are included. Only STATUS.md changed during the run, so the result stands for v1's code.
- **Vercel:** not deployed. `https://blue-visual-teacher.vercel.app/` returns `X-Vercel-Error: NOT_FOUND` on every path tried
  (`/`, `/web/index.html`, `/index.html`, `/dashboard`, `/api/health`), so the project name is reserved but no deployment exists
  behind it. CLI 65.4.0 available but `vercel whoami` reports logged out, and the keeper may not authenticate.
  Also `web/` alone is not deployable: it loads `../renderer/{engine,templates,theme}.js`, `/renderer/assets/fonts/*.ttf` (4 Noto
  faces) and `/fixtures/golden_manifest_en.json`. A 1.6 MB static bundle of `web/ + renderer/ + assets/fonts/ + fixtures/` with a
  `/` -> `/web/index.html` rewrite was assembled and verified locally at `?mock=1`: renders, no console errors, fonts local so the
  offline rule survives deployment.
- **Note:** test accounts `keeper.test@example.com` and `keeper.ui.1793126398729@example.com` (one Ohm's Law history row) were
  created in `exporter/data/bvt.db` while proving the auth and history endpoints. Delete the DB to reset.
- **Waiting on owners:** AYUSH (stale branch, dashboard banners), FARHAN (code_walkthrough template, next/replay), TARUN (Indian
  English voice default, device hardcode).

**Two keeper sessions ran Pass 1 independently** (AYUSH's at 00:10, YYUG's ending 00:04). Where they differ, the evidence:

- `ayush/*` "already incorporated": content yes, commits no. `git cherry v1 origin/ayush/frontend` lists all 4 commits as not in v1,
  and merging the branch would regress `exporter/app.py`. Outcome is the same either way: it must not be merged.
- "Gate: Green (D1-D10 10/10)": that table is the 2026-10-27 19:22-20:20 rerun. The first fresh full run on current v1 is the
  204-passed result above, so green holds -- now with a current timestamp behind it.
- "Blockers: None": open items are in Handoffs -- dashboard banners (fixed on `yyug/dashboard-banners`, see Pass 2), the
  `app/layout.tsx` offline violations, and nothing deployed at the Vercel URL.

**From Pass 2 on, one keeper pushes to v1** -- two agents merging and pushing the same branch is the race this role exists to prevent.

### Pass 2 (YYUG keeper session) · 2026-10-28 00:35

- **Rebased** onto AYUSH's `d1c1223` (his keeper log + CC-1 vote). Two STATUS.md conflicts, both resolved keeping both sides:
  his `AYUSH ✅` vote on CC-1 kept, his Pass 1 kept verbatim, mine placed beside it with the reconciliation note above.
- **Merged:** `yyug/dashboard-banners` (`86a39e3`, merge `b6388e2`) -- the dashboard now renders real history from
  `GET /api/lessons/history` and only shows the demo banner for a tokenless local session. 3 files, frontend only.
  Verified live before merging: a fresh user signed up, generated Ohm's Law, and the dashboard listed it.
- **Gate on the merge:** `tsc --noEmit` exit 0 · `next build` compiles, `/dashboard` prerendered · `tests/test_ui.py` +
  `tests/test_e2e_offline.py` 10 passed, 3 skipped · renderer 18/18 · `test:units` 12 + 5. Full suite on the pre-merge code:
  204 passed, 3 skipped (Pass 1). The merge changes no Python.
- **Held:** `yyug/code-walkthrough` (`cc3597b`, owner YYUG). Two reasons. (1) Until FARHAN's `code_walkthrough` template exists,
  the planner can now choose a scene type that nothing renders, and the judges' Python-loops sample is the topic most likely to
  trigger it -- merging the schema alone makes that demo worse, not better. Merge it together with his template. (2) It was cut
  from the pre-rebase `96cd58c`, so it must be replayed first: `git rebase --onto v1 96cd58c yyug/code-walkthrough`; a plain
  merge drags in duplicate docs commits. Not yet full-suite tested (its own run was stopped to free RAM for the baseline).
- **Skipped:** `origin/ayush/frontend` -- unchanged, still stale.
- **Decision recorded:** the Next UI is the product UI (Handoffs, 00:30).
- **Vercel:** unchanged -- nothing deployed at the URL, CLI logged out on this machine.
- **Waiting on owners:** AYUSH (STEP 0-4 prompt sent 00:25: sync, offline fixes in `app/layout.tsx`, hardcoded
  `127.0.0.1:8000` in `app/lesson/[id]/page.tsx:28` and `components/app/lesson-view.tsx:24-25`, next-scene/replay, level +
  length inputs) · FARHAN (code_walkthrough template, `web/` next/replay) · TARUN (Indian-English voice default, device hardcode).

### Pass 3 (YYUG keeper session) · 2026-10-28 01:05

- **Decision (user):** the Vercel URL serves the Next UI as a shop window, with a clear "run locally to generate" state.
- **Merged:** `yyug/vercel-showcase` (`055c77f`, merge `9956aa3`), 8 files, frontend only. On a public host with no
  `NEXT_PUBLIC_API_BASE_URL`, `lib/api.ts` `request()` now fails at once with `ApiError('showcase')` instead of hanging 15 s
  against `<host>:8000`; the form, status card, app-shell banner and dashboard explain how to run it locally. A local install
  whose server is down gets a "start run_demo" panel instead of a red error. `?showcase=1` forces the mode locally for testing.
  Verified in a browser against a production build in all three modes (preview, server down, normal); preview made 0 requests
  to :8000. Normal generation unchanged (Ohm's Law -> `/lesson/34e9269a444e`, ready).
- **Gate on the merge:** `tsc --noEmit` exit 0 · `next build` OK · `tests/test_ui.py` + `tests/test_e2e_offline.py` 10 passed,
  3 skipped · renderer + `test:units` pass.
- **Vercel failure, narrowed but not solved:** a clean `git archive` of `origin/v1` + `npm ci` + `next build` succeeds, and
  `vercel build` with framework auto-detection gets through detection, build and function creation (it only stops on a
  Windows-local symlink EPERM that Linux builders do not have). All 70 local imports match tracked files with exact case, so a
  Windows-only case mismatch is ruled out. The remaining suspect is the Vercel project's own settings (Root Directory,
  Framework Preset, build/install command overrides). Logs need an account: `npx vercel inspect <deployment> --logs`.
- **Owner note (AYUSH):** this pass edited your `lib/api.ts`, `lesson-form.tsx`, `backend-status.tsx`, `app-shell.tsx` and
  `dashboard-view.tsx` with small hooks; the logic lives in three new files. If your STEP 3 work on `lesson-form.tsx` conflicts,
  your side wins -- keep the `submitError.offline` branch and the `!showcase` guard on the language warning.
