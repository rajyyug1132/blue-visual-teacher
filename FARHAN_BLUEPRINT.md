# FARHAN_BLUEPRINT.md — Renderer + Web UI

You own **everything the judge sees**: the canvas animation engine (`renderer/`) and the full user interface (`web/`). Visuals 15% + teaching quality 20% (visual clarity carries it) + part of "working end to end" 25% + speed 10% (the progress UI makes speed visible).
Read first: `CLAUDE.md`, `PLAN.md` (sections 3, 4.3, 4.4, 4.7). Contracts there are frozen.

---

## 1. Files you own

```
renderer/
  player.html        clean 1280x720 canvas page, NO UI. Used by Ayush's exporter (Playwright).
  engine.js          timeline, renderAtTime, scene transitions, captions, fonts
  templates.js       the 8 visual templates
  theme.js           colors, type scale, easing, text-fit helpers, seeded PRNG
  assets/fonts/      Noto Sans, Noto Sans Devanagari, Noto Sans Kannada, Noto Sans Tamil, Noto Sans Telugu (.ttf/.woff2)
web/
  index.html  app.js  style.css      the user interface (vanilla JS, no CDN, no frameworks that need the network)
```
Do not touch `orchestrator/`, `localization/`, `exporter/`. If you need an API change, edit PLAN.md section 4 and tell its owner.

## 2. Unblock yourself in the first 20 minutes

Tarun's real manifest will arrive later. Use a **hand-made manifest** so you can start immediately. Build it from `fixtures/golden_ohms_law.json`: for each scene, `duration_sec = words / 2.3 + 0.35`, cumulative `start_sec/end_sec`. Save as `fixtures/golden_manifest_en.json` (Tarun will overwrite it with the real one). No audio yet? `player.html` must still work silently: audio is optional.

## 3. Engine design (`renderer/engine.js`)

Public API (frozen, PLAN 4.4):
```js
window.initLesson(title, scenes, lang)  // async: await fonts, build timeline, resolve when ready
window.renderAtTime(t)                  // sync, pure function of t, draws one full frame
window.totalDuration                    // seconds
```
Rendering rules:
1. **Pure function of time.** `renderAtTime(t)` must give the same pixels every call. No `Date.now`, no `setInterval`, no `Math.random` (use `theme.rng(seed)` = mulberry32 seeded by scene id for decorative particles).
2. Find scene `i` where `start_sec <= t < end_sec` (clamp at the end). `lt = t - start_sec`, `p = lt / duration`.
3. Draw order: background -> header bar (lesson title, small) -> template for scene `i` -> caption bar -> scene progress dots (1..N) -> optional fade.
4. **Transitions:** the last 0.35 s of each scene is the silent tail added by TTS. Use it to fade/slide out the current visual and (in the first 0.35 s of the next) fade/slide in the next. Never hard-cut.
5. **Fonts:** before the first draw `await document.fonts.load('32px "Noto Sans Kannada"')` etc. for the lesson's script, then `await document.fonts.ready`. All fonts via `@font-face` with local URLs. Zero network requests. Font stack per lang:
   - en: `"Noto Sans", sans-serif`
   - hi: `"Noto Sans Devanagari", "Noto Sans", sans-serif`
   - kn: `"Noto Sans Kannada", "Noto Sans", sans-serif`
   - ta: `"Noto Sans Tamil", ...`  te: `"Noto Sans Telugu", ...`
6. Canvas 2D is enough. Use `ctx.fillText` (Chromium shapes Indic scripts correctly if the font is loaded). Do not use `ctx.letterSpacing` for Indic text (breaks ligatures).
7. **Text fitting helpers in `theme.js`:** `wrapText(ctx, text, maxWidth)` that wraps by words (Indic text is space-separated too), `fitText(ctx, text, box, maxPx, minPx)` that shrinks font until it fits, `truncate` as last resort with an ellipsis. Hindi/Kannada strings are ~1.3-1.8x longer than English: **every text draw goes through fitText.**
8. Errors never escape: wrap each template call in try/catch; on error draw the `bullets` template with the same params.

### Theme (`theme.js`)
- Palette: bg `#0B1530` (deep navy), panel `#13224A`, text `#F4F7FF`, muted `#9FB0D6`, accent `#3DA5FF` (blue), accent2 `#FFC53D` (amber), good `#4ADE80`, warn `#FB7185`.
- Type scale at 1280x720: title 56 px, headline 44 px, label 34 px (min 28), step 30 px (min 24), caption 30 px (min 24).
- Safe area: 64 px margins; caption bar y = 600..704; header y = 0..72.
- Easing: `easeOutCubic`, `easeInOutCubic`, `easeOutBack`. Stagger items by 0.18 s.
- Keep one accent color per scene (cycle blue/amber/green) so scenes feel distinct without clutter.

## 4. The 8 templates (`renderer/templates.js`)

Each template: `draw(ctx, params, lt, dur, theme, lang)` where `params = {labels:[], steps:[]}`. Items appear one by one (stagger 0.18 s, 0.5 s ease), then hold; everything is fully visible by `dur * 0.6` so the learner can read it while the narration finishes. Build in this order (important ones first):

| # | type | Layout and animation |
|---|---|---|
| 1 | `title` | `labels[0]` large centered headline (fit to 2 lines), other labels as chips below, `steps[0]` as subtitle in muted color. Animated accent underline sweeps in. |
| 2 | `bullets` | `labels[0]` heading top-left, `steps[]` as rows with a colored dot, each slides in from the left and fades in. |
| 3 | `compare` | Two columns (or three if 3 labels), each a rounded panel with the label as heading; `steps[]` shown as short lines below / between; arrow or "vs" badge between columns. |
| 4 | `equation` | `labels[0]` is the main formula, huge, center, with a glow pulse; `labels[1..]` are legend rows (symbol : meaning) revealed one by one on the left/right; `steps[]` derived forms shown below as smaller formulas. |
| 5 | `flow` | `labels[]` are boxes laid out horizontally (wrap to 2 rows if >3), connected by arrows that draw themselves; a highlight dot travels along the path; `steps[0]` is the result strip at the bottom. |
| 6 | `labeled_diagram` | Central rounded box or circle with `labels[0]` inside; remaining labels as callouts around it with leader lines drawing in; `steps[]` as numbered chips at the bottom. |
| 7 | `timeline` | Horizontal line with N nodes (N = labels length); nodes pop in sequentially; label above, `steps[i]` (if present) below; a marker moves along the line. |
| 8 | `graph` | Parse numbers from `steps` (format `"name: 12"` or any number). If >= 2 numbers: animated bar or line chart with axis labels from `labels[0]` (x) and `labels[1]` (y). If not numeric: draw an illustrative rising curve with the two axis labels so the scene is never empty. |

Graceful degradation: unknown type, empty labels, or template exception -> `bullets`. Never throw, never blank.

Visual quality bar (this is the 15% and half of the 20%): one idea per scene, big readable text, lots of margin, consistent spacing, motion that explains (arrows drawing, values counting up) not decorating. Test every template with Hindi and Kannada strings from Tarun's real output as soon as they exist.

## 5. Captions

Bottom bar, current scene narration, translated text.
- Wrap to max 2 lines (shrink to min 24 px; if still too long, 3 lines).
- Word-by-word highlight: split by spaces, weight each word by character length; word `k` is active between `start + 0.15 + frac_k * (dur - 0.5)`. Active word accent color, past words full white, future words muted.
- Toggle captions on/off in the web UI (the exporter always burns them in).

## 6. `player.html` (used by the exporter) vs the in-app player

`renderer/player.html`:
- Just `<canvas id="stage" width="1280" height="720">` plus the scripts and `@font-face` rules. No controls, no scrollbars, black body margin 0.
- Exposes the three globals and nothing else. Optionally `window.ready = true` after `initLesson` resolves (Ayush waits on it).
- Must also work standalone: `player.html?manifest=/artifacts/ohms_law_en/manifest.json` loads the manifest, builds the lesson, plays with `<audio>` (hidden) as the clock, and draws with `requestAnimationFrame(() => renderAtTime(audio.currentTime))`. If there is no audio, use `performance.now()` as the clock in this playback mode only (never inside `renderAtTime`).
- Debug mode `?debug=1`: show a scrubber slider and current `t` so you can drag through every frame.

In the web UI the same `engine.js` runs inside the page's own canvas (not an iframe) so there is one code path.

## 7. Web UI (`web/`) — the part judges touch first

Single page, vanilla JS, dark navy theme matching the canvas, works on a 1366x768 laptop with Wi-Fi off. **No CDN, no external fonts, no analytics.** Serve fonts from `renderer/assets/fonts`.

Layout (top to bottom):
1. **Header:** product name ("Blue Visual Teacher"), a small "Offline" badge (green dot) that stays true: it also shows a live check (`navigator.onLine === false` -> "Running fully offline").
2. **Input row:** big text box ("What do you want to learn? e.g. Photosynthesis"), language chips `English | हिन्दी | ಕನ್ನಡ | தமிழ் | తెలుగు` (hide any language the backend reports as unavailable via `GET /api/languages`), **Generate** button (Enter key works).
3. **Example topics:** 8-10 clickable chips (Ohm's Law, Photosynthesis, Binary Search, Pythagoras Theorem, Water Cycle, Supply and Demand, Newton's Third Law, Monsoon, DNA Replication, GST). These are pre-cached so the demo never waits.
4. **Progress:** 5-step stepper `Plan > Translate > Voice > Render > Export` with the active step animated, a percent bar, and elapsed seconds per finished step (judges score speed, show it). On `error`, show a toast with a friendly message and a **Retry** button; never show a stack trace.
5. **Player card:** canvas 16:9, play/pause, scrubber, mute, captions toggle, language switcher that re-uses the cached plan (calls generate again with the new language; show "Cached plan, translating only"). Autoplay when ready.
6. **Actions:** **Download MP4** (link to the artifact), **Copy plan JSON** (small), **Show timings** (collapsible panel with stage seconds + telemetry like model name, tokens, fallback used).
7. **Footer:** one line listing the offline stack (Ollama + IndicTrans2 + Kokoro/MMS-TTS) so judges see the engineering.

Behavior:
- `POST /api/generate {topic, lang}` -> `{job_id}`. Poll `GET /api/status/{job_id}` every 400 ms. Response: `{stage, pct, stage_times, telemetry, error, mp4_url, manifest_url}`. Stages in order: `plan, translate, tts, render, encode, done`.
- When done: fetch `manifest_url` and the audio next to it, call `initLesson`, show the player, show the download button with `mp4_url`.
- Keyboard: Enter generates, Space plays/pauses.
- Accessibility: contrast >= 4.5:1, focus rings, labels on controls.
- Persist last topic/lang in `localStorage` wrapped in try/catch.
- Empty or very long topic (> 120 chars): inline validation, no request.
- Backend unreachable: friendly "Server not reachable, is `run_demo` running?" message.

Until Ayush's API exists, mock it: `web/mock.js` with the same endpoints implemented by `fetch` interception returning the golden manifest after a fake 6 s staged progress. Switch with `?mock=1`.

## 8. Timeline for you

| By | Deliverable |
|---|---|
| 12:30 | `player.html` + `engine.js` + `title` and `bullets` templates drawing the golden manifest; scrubber works. |
| 14:00 | 5 core templates (title, bullets, compare, equation, flow) + captions with highlight + fonts bundled; export works with Ayush's script. UI skeleton with mock API. |
| 18:00 | Real API wired; HI + KN strings render without overflow; transitions; progress stepper; download button. |
| 22:00 | `labeled_diagram`, `timeline`, `graph`; polish pass; error states; example chips; timings panel. |
| Overnight | Fix every layout bug found by the 20-topic harness (Ayush will send you the failing frames). |
| Freeze | No visual changes after the freeze; only bug fixes. |

## 9. Acceptance tests

1. Scrub `renderAtTime(0..total)` in steps of 0.05 s with the golden manifest in en, hi, kn: no console errors, no blank frame, no text outside the safe area.
2. Same input, two runs: frame hashes identical (determinism).
3. Zero network requests (DevTools Network tab with Wi-Fi off; also Ayush's request audit).
4. Every template tolerates: 1 label / 6 labels, empty `steps`, 60-character labels, Kannada strings 1.8x longer.
5. UI: full flow from typing a topic to playing and downloading, using the mock; then with the real API.

## 10. Paste-ready Claude Code prompt

> Read CLAUDE.md, PLAN.md, FARHAN_BLUEPRINT.md. You own renderer/ and web/. Create fixtures/golden_manifest_en.json by computing scene timings from fixtures/golden_ohms_law.json (duration = words/2.3 + 0.35). Then build renderer/theme.js, engine.js, templates.js (order: title, bullets, compare, equation, flow, labeled_diagram, timeline, graph) and renderer/player.html with a ?debug=1 scrubber, exactly following the API in PLAN.md 4.4. Bundle Noto fonts locally (no network). Every text draw must go through fitText. Then build web/index.html, app.js, style.css per section 7 with a mock API (web/mock.js, ?mock=1). Commit small and often on branch farhan/ui and push. Do not touch other folders.
