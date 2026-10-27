# CLAUDE.md — offline multilingual lesson-video pipeline
HARD RULES
1. OFFLINE ONLY. Set HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1 at process start. Never call any
   external API, CDN, Google Fonts URL, or cloud TTS/translation. Runtime must work with Wi-Fi off.
   The only allowed socket is the local Ollama daemon (localhost:11434).
2. DATA, NEVER CODE. The local LLM returns JSON matching LessonPlan.model_json_schema(). Never ask it
   for HTML/JS/SVG/Python/Manim. The renderer owns all drawing code.
3. PLAN IN ENGLISH ONLY. Indic text comes from IndicTrans2 (+ IndicProcessor) after validation.
4. AUDIO IS MASTER. TTS runs before rendering. Scene duration = measured audio length (tail pad
   0.35 s is already inside the audio; do not add it twice). Lesson total must be 30-90 s.
5. DETERMINISTIC RENDER. window.renderAtTime(t_sec) is a pure function of time. No setInterval,
   no unseeded Math.random, no Date.now inside the renderer.
6. Own folder only (see PLAN.md section 2). Contracts are in PLAN.md section 4.
   orchestrator/ = Yyug, localization/ = Tarun, renderer/ = Farhan, exporter/ = Ayush.
7. After every merge run: pytest tests/test_e2e_offline.py (and tests/test_orchestrator.py).
8. Keep code simple and readable. No new dependencies without telling the team.

OLLAMA NOTES (verified against ollama-python 0.6.3 / ollama 0.40.11)
- keep_alive must be the number -1, NOT the string "-1" (server returns 400 "missing unit in duration").
- think=False is accepted even by non-thinking models (qwen2.5:3b).
