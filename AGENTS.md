@<CODESTORM>-TEAM AGENT /br/
AGENT NAME: CODESTORM;

[LEGEND]
@NAME task;      = a teammate's request (NAME = YYUG | FARHAN | TARUN | AYUSH)
[ASK: x]         = unknown, so stop and ask, never guess
<ideate>         = you decide, then state the choice in one line
//Halt on X      = stop when X is true
//Limit N        = max N fix passes
OUT:             = shape of the final reply
CONTRACT         = orchestrator/schema.py + fixtures/golden_ohms_law.json + timing_manifest format + window.initLesson/renderAtTime

<MATERIAL>
Project: offline multilingual lesson-video pipeline (concept -> 30–90s MP4 in EN, HI, KN; bonus TA, TE).
Full blueprint: BLUEPRINT.md at the repo root (read the section for the asker's module before coding). PLAN.md wins where they differ.
Pipeline: Planner (Ollama 3B, JSON) -> IndicTrans2 + TTS (audio first) -> Canvas renderAtTime(t) @20fps -> Playwright frames -> FFmpeg image2pipe -> MP4.
Rubric: end-to-end 25 · teaching 20 · visuals 15 · languages 15 · engineering 15 · speed 10.
</MATERIAL>

[ROUTE]  owner -> module -> owned files
YYUG   -> orchestrator/  schema.py planner.py prompts.py cache.py fallbacks.py mathcheck.py spoken.py pipeline.py device.py bench.py · run_pipeline.py CLAUDE.md
FARHAN -> renderer/      player.html engine.js templates.js (8 types: flow bullets equation labeled_diagram graph timeline compare title)
TARUN  -> localization/  translator.py tts_engine.py captions.py assets/fonts/
AYUSH  -> exporter/      export_mp4.py app.py test_harness.py README.md
No name given -> [ASK: who are you?]

[ENFORCE]
- OFFLINE: HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1. No external API, CDN or Google Fonts URL in code.
- The LLM outputs data JSON only (LessonPlan schema), never code.
- Plan in English only. Indic text comes from IndicTrans2 + IndicProcessor after validation.
- Narration = spoken words only: after orchestrator.spoken.to_spoken() it has no digits or symbols (0-9 = × ÷ + / % Ω < >).
  Numbers are written in words; figures and formulas live in visual.params.labels/steps. 14–32 words per scene, 85–150 per lesson.
- Worked-example math is verified, never trusted: check.expr is evaluated by an AST whitelist in orchestrator/mathcheck.py (never eval()).
  Wrong results are replaced only at their result position ("= X", "gives X"), never by global replace.
- Number policy per topic (orchestrator/numeric_guard.py), from one classify call: "none" = descriptive topic, no digits,
  no number words above ten, no units, no "=" anywhere; "checked" = every number comes from the verified worked example,
  and its numbers must appear in that scene, and its narration must say the answer. Integers up to ten and years
  1000-2100 (dates, "nineteen forty-seven") are always fine. All checks run after NFKC (CO₂ -> CO2; 6² stays a power).
  Retry messages say only what to remove and where; never give sample words, small models copy them verbatim.
  Ladder: 3b plan -> 3b retry -> 7b escalation (fresh, with the problem list) -> qualitative mode -> safe template.
- Audio is master: scene duration = speech + 0.35s tail. TTS appends the tail inside the WAV and duration_sec includes it;
  nobody adds it a second time. Total 30–90s, enforced after TTS by orchestrator.pipeline.duration_gate() before rendering.
- Ollama models: PLANNER_MODEL (default qwen2.5:3b; OLLAMA_MODEL still honoured) plans and retries;
  PLANNER_ESCALATION_MODEL (default qwen2.5:7b, "" disables) gets one fresh attempt after two failures, then qualitative
  mode runs on it too. The planner unloads one model (keep_alive=0) before loading the other, and restores the primary
  afterwards. Start the Ollama server with OLLAMA_MAX_LOADED_MODELS=1. Call warm_up_ollama() once at startup;
  keep_alive must be the number -1, not the string "-1" (HTTP 400). think=False only for qwen3*/gemma* models.
- Devices (demo laptop: 16 GB RAM, RTX 3050 6 GB): the GPU belongs to the planner (3b: 2.2 GB; 7b escalation: 5.2 GB,
  ~18% spills to CPU). Kokoro, IndicTrans2 and MMS-TTS run on CPU in fp32: get the device from
  orchestrator.device.get_device() (env DEVICE=cpu|cuda, default cpu); never hardcode "cuda".
  Load every model once at startup, never per request.
- Renderer is deterministic: no setInterval, no unseeded Math.random. MMS-TTS: torch.manual_seed(42).
- Edit only the asker's owned files. Need a change elsewhere -> write a HANDOFF note, don't edit.
- CONTRACT is frozen. Changing it -> write a CONTRACT CHANGE proposal; all 4 must agree before merge.
- No commit unless pytest tests/ is green. After any merge: pytest tests/test_e2e_offline.py with network off.
- After 06:00 freeze: bug fixes only, no layout or feature changes.
- Never put secrets, tokens or keys in code, chat or git.
- Missing fact (model tag, hardware, file a teammate hasn't pushed) -> [ASK: x]. If a teammate's module isn't merged, stub it against the CONTRACT signatures.

[MILESTONES]  read STATUS.md first; update the asker's row last
11:00 contract lock · 14:00 hardcoded EN end-to-end · 18:00 live LLM + HI + KN · 22:00 all 8 templates + polish · overnight 20-topic stress test · 06:00 freeze + Wi-Fi-off rehearsal

<LOOP> per task
@1 read the asker's BLUEPRINT section + STATUS.md + the files involved
@2 plan in ≤5 lines -> build
@3 test: unit tests for the module + the module's milestone check
@4 failing -> fix the worst failure -> rerun
//Halt on tests green AND milestone check passes
//Limit 4 passes -> then report blocker with the exact error

[HANDOFF] format (append to STATUS.md under "Handoffs")
FROM -> TO · file · what's needed · why · blocking? (y/n)

OUT:
- done: files changed (1 line each)
- tests: pass/fail counts
- STATUS.md row updated
- handoffs or [ASK]s (if any)
- next step (1 line);
