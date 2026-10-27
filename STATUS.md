# Project Status Board

## Milestones
- [x] **11:00** Contract lock (`orchestrator/schema.py`, `fixtures/golden_ohms_law.json`, `CLAUDE.md`)
- [x] **14:00** Hardcoded EN end-to-end (`golden_manifest_en.json` delivered; unblocks Farhan & Ayush)
- [ ] **18:00** Live LLM + HI + KN (Ollama 3B + IndicTrans2 + Kokoro/MMS-TTS)
- [ ] **22:00** All 8 templates + UI polish
- [ ] **Overnight** 20-topic stress test across EN, HI, KN
- [ ] **06:00** Feature freeze + Wi-Fi-off rehearsal

## Module Status
| Teammate | Module | Files Owned | Status | Notes |
|---|---|---|---|---|
| **Yyug** | `orchestrator/` | `schema.py`, `planner.py`, `prompts.py`, `cache.py`, `fallbacks.py`, `run_pipeline.py`, `CLAUDE.md` | Merged | Planner, Tier 1 cache, safe fallbacks & CLI verified |
| **Farhan** | `renderer/` | `player.html`, `engine.js`, `templates.js`, `theme.js` | In Progress | Canvas renderer & 8 templates (UNBLOCKED by `golden_manifest_en.json`) |
| **Tarun** | `localization/` | `translator.py`, `tts_engine.py`, `captions.py`, `normalize.py`, `warmup.py`, `verify_l1_to_l8.py`, `assets/fonts/` | Done (L1–L8 Verified) | Full L1–L8 pipeline verified: offline sockets blocked, 1 batched IndicTrans2 call, zero Devanagari in KN, 24kHz MMS seed 42, 0.90 peak norm, 30–90s sync ±0.05s, 8 Noto fonts |
| **Ayush** | `exporter/` | `export_mp4.py`, `app.py`, `test_harness.py`, `README.md` | In Progress | Exporter & FastAPI backend (UNBLOCKED by `golden_manifest_en.json`) |

## Handoffs
- TARUN -> FARHAN · `fixtures/golden_manifest_en.json` · English audio timing manifest delivered (54.79s total, exact scene durations) · unblocks renderer `initLesson` & audio clock · blocking: n
- TARUN -> AYUSH · `fixtures/golden_manifest_en.json` · English audio timing manifest delivered · unblocks Playwright + FFmpeg export testing · blocking: n
- TARUN -> YYUG · `orchestrator/schema.py` · Recommend allowing non-English plans to bypass 8-word minimum in `check_word_budget` (handled safely in `translator.py` via `ensure_word_budget`) · blocking: n
