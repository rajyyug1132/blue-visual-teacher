# LEARNINGS-farhan.md — Farhan's Log & Decisions

## Pass 1 — Web UI Implementation & F1–F10 Validation

### Discoveries & Decisions
1. **Initial Blank Frame at t=0 (F2)**:
   - *Observation*: Initial easing `theme.easeOutCubic(lt / 0.6)` yielded alpha 0.0 at exact `t = 0.00s`, rendering a bare background prior to animation start.
   - *Fix*: Set minimum base presence (`Math.max(0.25, ...)`) for the scene headline / primary element across all visual templates, ensuring that the initial poster frame / thumbnail is immediately informative and never blank.

2. **Font Readiness & Deterministic Frame Hashing (F3)**:
   - *Observation*: Initial font probe over HTTP triggers asynchronous fallback resolution in Chromium when local TTF assets are pending from the localization module. A premature capture before the initial font layout settles can record transient metrics.
   - *Fix*: Added `Promise.allSettled([document.fonts.load(...)])` in `initLesson` per FARHAN_BLUEPRINT §3, and ran a warm-up pass before benchmark comparisons. Subsequent passes are 100% bitwise identical across all 3,686,400 raw RGBA canvas bytes.

3. **Web UI Architecture (F8, F9, F10)**:
   - Created single-page dark navy application in `web/` (`index.html`, `app.js`, `style.css`, `mock.js`).
   - Built zero-dependency `server.js` using Node.js standard libraries, mapping `/` to `/web/index.html?mock=1` and serving static renderer and fixture assets with CORS headers.
   - Added 5-step stepper with real-time stage seconds (`plan`, `translate`, `tts`, `render`, `encode`), live offline status indicator (`navigator.onLine === false`), 10 example topics, player controls (Space/Enter shortcuts, captions toggle, scrubber, mute), MP4 download link, and JSON copy button.
   - Verified zero non-local network requests across full generation and playback flow.
