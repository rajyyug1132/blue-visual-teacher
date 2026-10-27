Offline Multilingual Lesson-Video Pipeline: Complete Engineering Blueprint and Hackathon Execution GuideAt Hour 1.5 of the hackathon, your highest-leverage move is locking the JSON contract across all four workstreams within the next 15 minutes so that You (Orchestrator and LLM Planning), Farhan (Visual Engine and Templates), Tarun (IndicTrans2, TTS, Fonts, and Captions), and Ayush (Playwright, FFmpeg Export, Web UI, and Test Harness) can build in parallel without integration collisions. Because the judging rubric weights working end-to-end (25%), teaching quality (20%), visuals (15%), languages (15%), engineering (15%), and speed (10%), a deterministic pipeline that exports synchronized English, Hindi, and Kannada MP4s with Wi-Fi disabled will consistently outscore complex animations that drift out of sync or crash offline.By inverting the conventional video-first architecture—generating and measuring scene narration audio first, setting each scene's visual duration equal to its exact audio duration, and driving a seekable render(t) canvas function captured at 20 frames per second (fps) into FFmpeg's image2pipe—you eliminate audio-caption-visual drift by design. Parking TokenScope, Viralyst, and the virality model as standalone products while repurposing TokenScope's token-budgeting mechanics inside your 3B LLM planner keeps structured JSON payloads compact (~576 tokens across 5 scenes), ensuring fast local generation that maps reliably into the required 30–90 second video window.Across the four parallel workstreams, the end-to-end data handoff operates in four sequential stages: (1) the Planner and Schema Validator uses local Ollama and Pydantic's model_json_schema() to emit a validated ~576-token, 5-scene English JSON plan; (2) the Batched Localization and Parallel TTS stage translates strings via IndicTrans2 (200M) and synthesizes scene audio via Kokoro-82M (24 kHz native) or MMS-TTS (16 kHz resampled to 24 kHz); (3) the Seekable Browser Renderer draws the active scene and progressive Noto Sans captions onto an HTML5 Canvas via render(t); and (4) the Export Muxer streams 20 fps screenshots from Playwright into FFmpeg's image2pipe to encode a libx264 (yuv420p) MP4.1. Immediate 15-Minute Lock: Schema Contract, Golden Fixture, and CLAUDE.mdBefore anyone writes module code, commit three files to the repository root: CLAUDE.md (to govern Claude Code sessions), orchestrator/schema.py (the Pydantic data contract), and fixtures/golden_ohms_law.json (the hardcoded 5-scene English fixture for the 14:00 milestone).1.1 Drop-In CLAUDE.md for Module-Level AI CodingSave the following specification as CLAUDE.md in the repository root so every team member's Claude Code session obeys the hackathon's air-gapped rules and module boundaries:CLAUDE.md — Offline Multilingual Lesson-Video Pipeline Rules1. Hard Constraints (Zero Exceptions)OFFLINE ONLY: Set HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1 at process start. Never call OpenAI, Anthropic, Google, Bhashini, ElevenLabs, or any external HTTP API, CDN, or Google Fonts URL.DATA ONLY, NEVER CODE: The local Ollama LLM outputs strictly constrained JSON matching LessonPlan.model_json_schema(). Never ask the LLM to generate Manim, Python, HTML, SVG, or JavaScript code.ENGLISH PLANNING ONLY: The 3B LLM plans only in English (eng_Latn). All Indic text (hin_Deva, kan_Knda, tam_Taml, tel_Telu) is produced post-validation via IndicTrans2 + IndicProcessor.AUDIO-MASTER TIMING: TTS runs before visual rendering. Scene i duration D_i = audio_length_i + 0.35s. Total lesson duration must land in [30.0, 90.0] seconds (target: 45–65s across 4–6 scenes).DETERMINISTIC SEEKABLE RENDERER: Visuals are rendered via window.renderAtTime(t_sec) on a 1280x720 HTML5 Canvas at 20 FPS. No setInterval or unseeded Math.random() inside the renderer.2. Module Boundaries & File Ownershiporchestrator/ (Owner: You): schema.py, planner.py, prompts.py, cache.py, fallbacks.py.localization/ (Owner: Tarun): translator.py (IndicTrans2), tts_engine.py (Kokoro-82M + MMS-TTS), captions.py, assets/fonts/.renderer/ (Owner: Farhan): player.html, engine.js, templates.js (8 fixed visual types: flow, bullets, equation, labeled_diagram, graph, timeline, compare, title).exporter/ (Owner: Ayush): export_mp4.py (Playwright + FFmpeg image2pipe), app.py (FastAPI/UI), test_harness.py, README.md.3. Integration GateRun pytest tests/test_e2e_offline.py with network interfaces disabled after every merge.1.2 Locked Pydantic Schema (orchestrator/schema.py)Ollama converts a Pydantic BaseModel into a formal GBNF grammar when passed via format=LessonPlan.model_json_schema(), constraining token sampling at the logit level so the 3B model cannot emit markdown fences, conversational preambles, or unapproved visual types. Because schema enforcement only guarantees structural shape and not semantic conciseness, add a Pydantic @field_validator on narration to enforce per-scene word counts that keep total audio duration inside the 30–90 second target.Python# orchestrator/schema.py
from typing import List, Literal
from pydantic import BaseModel, Field, field_validator

VisualType = Literal[
    "flow", "bullets", "equation", "labeled_diagram",
    "graph", "timeline", "compare", "title"
]

class VisualParams(BaseModel):
    labels: List[str] = Field(
        default_factory=list,
        min_length=1,
        max_length=6,
        description="1 to 6 concise labels (max 5 words each) for nodes, axes, or headers."
    )
    steps: List[str] = Field(
        default_factory=list,
        min_length=1,
        max_length=5,
        description="1 to 5 ordered steps, bullet points, comparison rows, or equation breakdown lines."
    )

class VisualSpec(BaseModel):
    type: VisualType
    params: VisualParams

class SceneSpec(BaseModel):
    id: int = Field(..., ge=1, le=6)
    narration: str = Field(
        ...,
        min_length=25,
        max_length=240,
        description="1-2 short spoken sentences (18-30 words). Plain spoken text, no markdown."
    )
    visual: VisualSpec
    caption_key: Literal["narration"] = "narration"

    @field_validator("narration")
    @classmethod
    def check_word_budget(cls, v: str) -> str:
        words = v.strip().split()
        if len(words) < 8 or len(words) > 42:
            raise ValueError(f"Scene narration must be 8-42 words (got {len(words)}) to fit 30-90s audio budget.")
        return v.strip()

class LessonPlan(BaseModel):
    title: str = Field(..., min_length=3, max_length=90)
    language_neutral: bool = True
    scenes: List[SceneSpec] = Field(..., min_length=4, max_length=6)
1.3 Golden Hardcoded Fixture (fixtures/golden_ohms_law.json) for the 14:00 MilestoneDistribute this exact JSON to Farhan, Tarun, and Ayush immediately so they can build and test their modules before the live LLM planner is wired in. It contains 2,077 characters (~576 tokens) and 122 spoken words across 5 scenes ([22, 27, 24, 28, 21] words). At a natural TTS speaking rate of 2.3 words/second plus a 0.35-second silence tail per scene, it produces scene durations of 9.92s, 12.09s, 10.78s, 12.52s, and 9.48s—a total video duration of 54.79 seconds (1,096 frames at 20 fps), centered inside the 30–90 second requirement:JSON{
  "title": "Ohm's Law: Voltage, Current, and Resistance",
  "language_neutral": true,
  "scenes": [
    {
      "id": 1,
      "narration": "Why does your phone charger get warm while fast-charging, or a ceiling fan slow down when voltage drops during summer in Bengaluru?",
      "visual": {
        "type": "title",
        "params": {
          "labels": ["Ohm's Law", "V = I × R", "Voltage, Current & Resistance"],
          "steps": ["Everyday Electricity in India"]
        }
      },
      "caption_key": "narration"
    },
    {
      "id": 2,
      "narration": "Think of an overhead water tank on your house roof. Water height is Voltage, water flow through the pipe is Current, and a narrow tap is Resistance.",
      "visual": {
        "type": "compare",
        "params": {
          "labels": ["Roof Tank Height → Voltage (V)", "Pipe Water Flow → Current (I)", "Narrow Tap → Resistance (R)"],
          "steps": ["Higher pressure pushes more flow", "Narrower pipe restricts flow"]
        }
      },
      "caption_key": "narration"
    },
    {
      "id": 3,
      "narration": "Georg Ohm discovered that Voltage equals Current multiplied by Resistance: V equals I times R. Doubling voltage doubles the current if resistance stays constant.",
      "visual": {
        "type": "equation",
        "params": {
          "labels": ["V = I × R", "V : Voltage (Volts)", "I : Current (Amperes)", "R : Resistance (Ohms Ω)"],
          "steps": ["I = V / R", "R = V / I"]
        }
      },
      "caption_key": "narration"
    },
    {
      "id": 4,
      "narration": "Let's test a 230-Volt Indian wall socket connected to an iron box with 46 Ohms resistance. Dividing 230 Volts by 46 Ohms gives exactly 5 Amperes of current.",
      "visual": {
        "type": "flow",
        "params": {
          "labels": ["Supply: V = 230 V", "Heater Coil: R = 46 Ω", "Formula: I = V / R", "Result: I = 5 A"],
          "steps": ["230 V ÷ 46 Ω = 5 Amperes"]
        }
      },
      "caption_key": "narration"
    },
    {
      "id": 5,
      "narration": "To recap: Voltage pushes electrons, Resistance opposes them, and Current is the resulting flow governed by V equals I times R.",
      "visual": {
        "type": "bullets",
        "params": {
          "labels": ["Key Takeaways: Ohm's Law"],
          "steps": [
            "Voltage (V): Electrical pressure in Volts",
            "Resistance (R): Opposition to flow in Ohms (Ω)",
            "Current (I = V / R): Flow rate in Amperes"
          ]
        }
      },
      "caption_key": "narration"
    }
  ]
}
2. Your Module: Orchestrator, Token-Constrained 3B Planner, and Pedagogical PromptingYour module (orchestrator/) controls Teaching Quality (20%), Reliability/Engineering (15%), and Planning Speed (10%). Small 3B-class models fail in two ways when left unconstrained: they either generate overly verbose text that pushes video duration past 90 seconds, or they emit malformed JSON keys. Embedding token-length constraints into your Ollama call parameters and Pydantic validator turns a local 3B model into a fast, predictable curriculum planner.2.1 Local Ollama Model Selection and the Thinking Mode TrapChoose your local Ollama checkpoint according to your demo laptop's hardware profile, and explicitly disable thinking tokens (think=False) in every API call.Ollama Model TagEffective Params & File SizeMemory ProfileReported GPU SpeedReported CPU / Community ProfileHackathon Recommendation & Critical Settingsllama3.2:3b3.2B (~2.0 GB)2.8 GB RAM on RPi 5~135 tok/s modeled decode (Fast-1B/3B tier)14s avg response on CPU-only RPi 5 (16 GB)Primary 3B Baseline. Non-thinking model that handles familiar domains without looping. Set temperature=0.gemma4:e2b / e4b2.3B (1.5 GB) / 4.5B (3.0 GB)Fits edge/laptop RAM150 tok/s (e2b) / 120 tok/s (e4b) on RTX 5090 (Q4_K_M)6.88 tok/s on CPU (e4b), high reasoning quality in r/LocalLLM testsStrong Alternative. Supports think controls; pass think=False to skip reasoning overhead.qwen3:4b / 1.7b4.0B (2.5 GB) / 1.7B (1.4 GB)8B sibling (5.2 GB) fits 8 GB VRAM90 tok/s for qwen3:8b on RTX 5090 (Q4_K_M)36s (0.6b) to 224–268s (1.7b+) on RPi 5 CPU if think is left enabledMust set think=False. Disabling thinking skips internal reasoning chains and outputs JSON directly.deepseek-r1:1.5b1.5BCompact reasoning distill92 tok/s for 7B sibling on RTX 509012 tok/s in r/LocalLLM tests; spent 47s fabricating on an unfamiliar promptAvoid for live demo. High fabrication risk and long <think> traces on open-ended prompts.Disabling thinking mode is critical for both latency and accuracy on compact models. A NeurIPS 2025 study on test-time scaling found that while initial thinking tokens improved accuracy from 82.2% (at 385 tokens) to 87.3% (at 1,100 tokens), pushing average thinking length further to 15,980 tokens degraded accuracy to 70.3% due to "overthinking". On CPU hardware, community benchmarks on a Raspberry Pi 5 reported that built-in thinking mode caused a 0.6B model (qwen3:0.6b) to take 36 seconds—4× slower than a comparable non-thinking model—while larger Qwen 3 models took 224 to 300 seconds. In Ollama (v0.6.2+), passing think=False in ollama.chat() instructs the runtime to skip the message.thinking step and immediately generate message.content.2.2 Applying Token-Budgeting Mechanics Inside the PlannerRather than deploying a separate external length-prediction model such as a DistilBERT proxy (S3 or SSJF) or an internal hidden-state probe (TRAIL or EGTP), you can enforce tight token and duration bounds directly inside your single-call Ollama orchestrator using four engineering controls:First, lock the audio duration to word-count ratio. At a natural speech synthesis rate of 2.2 to 2.5 words per second plus a 0.35-second silence tail per scene, a 5-scene lesson requires 90 to 150 total spoken words (18 to 30 words per scene) to land cleanly between 42 and 68 seconds. Second, account for JSON schema token overhead. In our 5-scene golden_ohms_law.json verification, 122 words of narration plus visual.params (labels and steps) and JSON syntax produced 2,077 characters, or ~576 output tokens (eval_count).Third, configure explicit context and prediction bounds (num_ctx and num_predict). Ollama defaults to a 2,048-token context window (num_ctx), which can silently truncate prompts containing few-shot examples and JSON schemas, and sets num_predict to -1 (which Ollama's server.go caps at 10 * num_ctx, allowing runaway generation). Because num_predict hard-truncates output if reached, set options={"temperature": 0, "num_ctx": 4096, "num_predict": 850} so a ~576-token plan has ample headroom to close its final JSON bracket while preventing infinite loops. Pass keep_alive="-1" so the model stays resident in memory indefinitely, eliminating multi-second load_duration penalties on live judge queries.Fourth, log Ollama's native nanosecond telemetry. Every non-streaming or final streaming response from /api/chat and /api/generate returns prompt_eval_count, prompt_eval_cached_count, prompt_eval_duration, eval_count, and eval_duration measured in nanoseconds (divide by 1e9 for seconds). Note that when repeated requests share the exact same system prompt and few-shot prefix, Ollama caches the prompt prefix—meaning prompt_eval_count may only report uncached delta tokens while prompt_eval_cached_count tracks the cached prefix. Keeping your system prompt and two few-shot examples strictly static at the top of messages maximizes this built-in prefix cache hit rate.2.3 Pedagogical System Prompt with Two Few-Shot Indian Examples (orchestrator/prompts.py)Judges allocate 20% to teaching quality, rewarding a clear pedagogical arc (Hook → Intuition/Analogy → Core Principle → Worked Example → Recap), relatable Indian examples, and strict visual-to-narration alignment (one visual concept per scene). Embedding two complete few-shot examples in your prompt trains the 3B model by demonstration to match both the 5-scene teaching structure and the ~20–28 word narration length:Python# orchestrator/prompts.py
SYSTEM_PROMPT = """You are an expert Indian STEM educator and visual curriculum planner.
Given a student's concept, output ONLY valid JSON matching the LessonPlan schema. Never output code or markdown.

MANDATORY 5-SCENE PEDAGOGICAL STRUCTURE:
- Scene 1 (Hook): A relatable everyday Indian question or phenomenon (18-26 words). Visual type: "title".
- Scene 2 (Intuition / Analogy): A concrete physical analogy from daily life in India—water tanks, cricket, IRCTC trains, UPI, traffic, or kitchen cooking (20-28 words). Visual type: "compare" or "labeled_diagram".
- Scene 3 (Core Principle / Mechanism): State the exact scientific, mathematical, or conceptual rule clearly (20-28 words). Visual type: "equation", "flow", or "timeline".
- Scene 4 (Worked Example): Walk through ONE concrete numerical or step-by-step example from start to finish (22-30 words). Visual type: "flow" or "graph".
- Scene 5 (Recap): Summarize the 3 essential takeaways so the student remembers the rule (18-25 words). Visual type: "bullets".

STRICT RULES:
1. Plan in clear, simple English ("language_neutral": true).
2. Each scene's "narration" MUST be 1-2 short spoken sentences (18-30 words). Total words across all 5 scenes MUST be 100-140 words so audio lasts 45-65 seconds.
3. Spell out spoken math in "narration" (write "V equals I times R", not raw LaTeX), and put symbolic formulas ("V = I × R") inside visual.params.labels.
4. Keep visual.params.labels (2-4 items) and visual.params.steps (1-4 items) under 6 words each so they translate cleanly into Hindi and Kannada without overflowing the canvas.
"""

FEW_SHOT_MESSAGES = [
    {"role": "user", "content": "Concept: Ohm's Law"},
    {"role": "assistant", "content": '{"title":"Ohm\'s Law: Voltage, Current, and Resistance","language_neutral":true,"scenes":[{"id":1,"narration":"Why does your phone charger get warm while fast-charging, or a ceiling fan slow down when voltage drops during summer in Bengaluru?","visual":{"type":"title","params":{"labels":["Ohm\'s Law","V = I × R","Voltage, Current & Resistance"],"steps":["Everyday Electricity in India"]}},"caption_key":"narration"},{"id":2,"narration":"Think of an overhead water tank on your house roof. Water height is Voltage, water flow through the pipe is Current, and a narrow tap is Resistance.","visual":{"type":"compare","params":{"labels":["Roof Tank Height → Voltage (V)","Pipe Water Flow → Current (I)","Narrow Tap → Resistance (R)"],"steps":["Higher pressure pushes more flow","Narrower pipe restricts flow"]}},"caption_key":"narration"},{"id":3,"narration":"Georg Ohm discovered that Voltage equals Current multiplied by Resistance: V equals I times R. Doubling voltage doubles the current if resistance stays constant.","visual":{"type":"equation","params":{"labels":["V = I × R","V : Voltage (Volts)","I : Current (Amperes)","R : Resistance (Ohms Ω)"],"steps":["I = V / R","R = V / I"]}},"caption_key":"narration"},{"id":4,"narration":"Let\'s test a 230-Volt Indian wall socket connected to an iron box with 46 Ohms resistance. Dividing 230 Volts by 46 Ohms gives exactly 5 Amperes of current.","visual":{"type":"flow","params":{"labels":["Supply: V = 230 V","Heater Coil: R = 46 Ω","Formula: I = V / R","Result: I = 5 A"],"steps":["230 V ÷ 46 Ω = 5 Amperes"]}},"caption_key":"narration"},{"id":5,"narration":"To recap: Voltage pushes electrons, Resistance opposes them, and Current is the resulting flow governed by V equals I times R.","visual":{"type":"bullets","params":{"labels":["Key Takeaways: Ohm\'s Law"],"steps":["Voltage (V): Electrical pressure in Volts","Resistance (R): Opposition to flow in Ohms (Ω)","Current (I = V / R): Flow rate in Amperes"]}},"caption_key":"narration"}]}'},
    {"role": "user", "content": "Concept: Binary Search"},
    {"role": "assistant", "content": '{"title":"Binary Search: Halving the Search Space","language_neutral":true,"scenes":[{"id":1,"narration":"How does a dictionary user or an Indian Railways PNR lookup find one record among millions in just twenty steps instead of checking every single entry?","visual":{"type":"title","params":{"labels":["Binary Search","O(log N) Time Complexity","Divide and Conquer"],"steps":["Fast Lookup in Sorted Data"]}},"caption_key":"narration"},{"id":2,"narration":"Imagine finding roll number 72 in a sorted exam sheet. Instead of reading from roll number 1, open the exact middle page and eliminate half instantly.","visual":{"type":"compare","params":{"labels":["Linear Scan: Check 1 by 1","Binary Search: Cut in Half"],"steps":["1,000,000 items → 1,000,000 checks","1,000,000 items → At most 20 checks"]}},"caption_key":"narration"},{"id":3,"narration":"Binary Search compares your target with the middle element. If the target is larger, discard the left half; if smaller, discard the right half.","visual":{"type":"flow","params":{"labels":["1. Find Mid = (Low + High) / 2","2. Compare Target vs A[Mid]","3. Halve Interval & Repeat"],"steps":["Requires Sorted Array","Halves Space Every Step"]}},"caption_key":"narration"},{"id":4,"narration":"Let\'s find 72 in sorted array 10, 30, 50, 72, 90. Middle is 50; since 72 is greater, keep the right half 72, 90 and find 72 next.","visual":{"type":"labeled_diagram","params":{"labels":["[10, 30, 50, 72, 90]","Step 1: Mid = 50 (< 72)","Step 2: Search [72, 90]","Found Target = 72!"],"steps":["2 Comparisons vs 4 in Linear Scan"]}},"caption_key":"narration"},{"id":5,"narration":"To recap: Binary Search requires sorted data, checks the midpoint each step, and runs in logarithmic time O of log N.","visual":{"type":"bullets","params":{"labels":["Binary Search Summary"],"steps":["Precondition: Data must be sorted","Mechanism: Halve search range each step","Speed: O(log₂ N) comparisons"]}},"caption_key":"narration"}]}'}
]
2.4 Validation, One-Retry Self-Correction, and Deterministic Fallback (orchestrator/planner.py)While format=LessonPlan.model_json_schema() enforces JSON structure, the 3B model can still occasionally violate word-count bounds. Implement a two-tier reliability guard: one automatic retry that appends the Pydantic ValidationError to the prompt, followed by a deterministic, concept-parameterized safe template fallback so the pipeline cannot crash during the live demo:Python# orchestrator/planner.py
import time
import ollama
from pydantic import ValidationError
from orchestrator.schema import LessonPlan
from orchestrator.prompts import SYSTEM_PROMPT, FEW_SHOT_MESSAGES

MODEL_NAME = "llama3.2:3b"  # Or "gemma4:e4b" / "qwen3:4b"

def warm_up_ollama(model: str = MODEL_NAME) -> None:
    """Pin model in memory at startup so live demo requests incur near-zero load_duration."""
    ollama.generate(model=model, prompt="ping", keep_alive="-1", options={"num_predict": 1})

def plan_lesson(concept: str, model: str = MODEL_NAME) -> tuple[LessonPlan, dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + FEW_SHOT_MESSAGES + [
        {"role": "user", "content": f"Concept: {concept.strip()}"}
    ]
    t0 = time.perf_counter()
    for attempt in range(2):
        resp = None
        try:
            resp = ollama.chat(
                model=model,
                messages=messages,
                format=LessonPlan.model_json_schema(),
                think=False,
                keep_alive="-1",
                options={"temperature": 0.0 if attempt == 0 else 0.2, "num_ctx": 4096, "num_predict": 850},
            )
            plan = LessonPlan.model_validate_json(resp.message.content)
            telemetry = {
                "attempt": attempt + 1,
                "prompt_tokens": getattr(resp, "prompt_eval_count", 0),
                "output_tokens": getattr(resp, "eval_count", 0),
                "eval_sec": round(getattr(resp, "eval_duration", 0) / 1e9, 3),
                "total_sec": round(time.perf_counter() - t0, 3),
                "fallback_used": False,
            }
            return plan, telemetry
        except (ValidationError, Exception) as exc:
            bad_content = getattr(resp.message, "content", "{}") if resp else "{}"
            messages.append({"role": "assistant", "content": bad_content})
            messages.append({
                "role": "user",
                "content": f"Validation failed: {exc}. Return corrected JSON with 4-6 scenes and 18-30 words per narration."
            })

    # Deterministic safe template fallback if both LLM attempts fail
    return build_safe_fallback_lesson(concept), {"attempt": 3, "fallback_used": True, "total_sec": round(time.perf_counter() - t0, 3)}

def build_safe_fallback_lesson(concept: str) -> LessonPlan:
    c = concept.strip().title()
    return LessonPlan(
        title=f"Understanding {c}: Core Principles & Application",
        language_neutral=True,
        scenes=[
            {"id": 1, "narration": f"Have you ever wondered how {c} works in everyday Indian technology and why engineers and scientists rely on it daily?", "visual": {"type": "title", "params": {"labels": [c, "Core Concept & Intuition", "Step-by-Step Guide"], "steps": [f"Mastering {c} in 60 Seconds"]}}, "caption_key": "narration"},
            {"id": 2, "narration": f"Think of {c} like organizing traffic at a busy Bengaluru junction: clear rules transform chaotic inputs into smooth, predictable outcomes.", "visual": {"type": "compare", "params": {"labels": [f"Without {c}", f"With {c}"], "steps": ["Unstructured & slow process", "Systematic & predictable result"]}}, "caption_key": "narration"},
            {"id": 3, "narration": f"At its core, {c} operates through three connected stages: receiving the input state, applying the governing transformation, and producing the verified output.", "visual": {"type": "flow", "params": {"labels": ["1. Input State", f"2. Apply {c} Rule", "3. Verified Output"], "steps": ["Deterministic transformation at each stage"]}}, "caption_key": "narration"},
            {"id": 4, "narration": f"In a practical example of {c}, when we change the primary input parameter, the output responds proportionally according to the system constraints.", "visual": {"type": "labeled_diagram", "params": {"labels": [f"{c} System", "Input Parameter", "Control Mechanism", "Measured Output"], "steps": ["Step 1: Measure input", "Step 2: Compute response"]}}, "caption_key": "narration"},
            {"id": 5, "narration": f"To recap {c}: remember the core mechanism, trace how inputs map to outputs, and apply this mental model to real-world problems.", "visual": {"type": "bullets", "params": {"labels": [f"Key Takeaways: {c}"], "steps": ["Understand the intuitive analogy", "Follow the 3-step input-to-output flow", "Verify results with a concrete example"]}}, "caption_key": "narration"},
        ]
    )
3. Tarun's Module: Offline Translation (IndicTrans2), Dual-Engine TTS, Fonts, and CaptionsTarun's module (localization/) governs Languages (15%) and audio-driven synchronization. All model weights and tokenizers must be pre-downloaded and loaded with os.environ["HF_HUB_OFFLINE"] = "1" and os.environ["TRANSFORMERS_OFFLINE"] = "1".3.1 Batched Translation with IndicTrans2 and the Mandatory IndicProcessorUse AI4Bharat's distilled 200M English-to-Indic checkpoint (ai4bharat/indictrans2-en-indic-dist-200M, 950 MB download size, MIT license; the 1B base model ai4bharat/indictrans2-en-indic-1B is 4.5 GB if VRAM permits).Using IndicProcessor(inference=True) from IndicTransToolkit (pip install indictranstoolkit) is mandatory for non-Devanagari languages. Because IndicTrans2 uses a unified Devanagari-based internal vocabulary across all supported Indic scripts, calling the model without IndicProcessor.preprocess_batch() and IndicProcessor.postprocess_batch() causes the decoder to emit raw Devanagari script even when translating into Kannada (kan_Knda), Tamil (tam_Taml), or Telugu (tel_Telu). The preprocessor normalizes text, extracts entity placeholders, and attaches language tags, while the postprocessor transliterates the decoded output from internal Devanagari space back into the target script (kan_Knda, tam_Taml, tel_Telu, or hin_Deva).To minimize translation latency, do not invoke model.generate() separately per scene. Flatten the lesson title, all 5 scene narrations, and all non-symbolic labels and steps (~25–30 strings total) into a single Python list, run one batched IndicTrans2 call, and unpack the translated strings back into a copy of LessonPlan. Filter out pure mathematical expressions (such as V = I × R) via a regular expression so symbolic formulas remain intact.Python# localization/translator.py
import os, re, copy
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from IndicTransToolkit import IndicProcessor
from orchestrator.schema import LessonPlan

LANG_CODE_MAP = {
    "en": "eng_Latn",
    "hi": "hin_Deva",
    "kn": "kan_Knda",
    "ta": "tam_Taml",
    "te": "tel_Telu",
}

FORMULA_REGEX = re.compile(r"^[\d\s\+\-\*\/\=\(\)\[\]\×\÷\Ω\→\<\>\:\,\.VIRAlogN_]+$")

class OfflineIndicTranslator:
    def __init__(self, ckpt_dir: str = "ai4bharat/indictrans2-en-indic-dist-200M"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.ip = IndicProcessor(inference=True)
        self.tokenizer = AutoTokenizer.from_pretrained(ckpt_dir, trust_remote_code=True, local_files_only=True)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            ckpt_dir,
            trust_remote_code=True,
            local_files_only=True,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
        ).to(self.device)
        self.model.eval()

    def translate_texts(self, texts: list[str], tgt_lang_short: str) -> list[str]:
        if tgt_lang_short == "en" or not texts:
            return texts
        tgt_lang = LANG_CODE_MAP[tgt_lang_short]
        translatable_idx, translatable_strs = [], []
        for idx, t in enumerate(texts):
            if FORMULA_REGEX.match(t.strip()):
                continue
            translatable_idx.append(idx)
            translatable_strs.append(t)

        if not translatable_strs:
            return texts

        batch = self.ip.preprocess_batch(translatable_strs, src_lang="eng_Latn", tgt_lang=tgt_lang)
        inputs = self.tokenizer(
            batch, truncation=True, padding="longest", max_length=256,
            return_tensors="pt", return_attention_mask=True
        ).to(self.device)

        with torch.inference_mode():
            generated = self.model.generate(
                **inputs, use_cache=True, min_length=0, max_length=256,
                num_beams=2, num_return_sequences=1
            )
        decoded = self.tokenizer.batch_decode(
            generated.detach().cpu().tolist(),
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        postprocessed = self.ip.postprocess_batch(decoded, lang=tgt_lang)

        result = list(texts)
        for idx, trans in zip(translatable_idx, postprocessed):
            result[idx] = trans
        return result

    def localize_lesson(self, plan: LessonPlan, lang: str) -> LessonPlan:
        if lang == "en":
            return plan
        localized = copy.deepcopy(plan)
        flat_strings = [localized.title]
        for s in localized.scenes:
            flat_strings.append(s.narration)
            flat_strings.extend(s.visual.params.labels)
            flat_strings.extend(s.visual.params.steps)

        translated = self.translate_texts(flat_strings, lang)
        cursor = 0
        localized.title = translated[cursor]; cursor += 1
        for s in localized.scenes:
            s.narration = translated[cursor]; cursor += 1
            n_labels = len(s.visual.params.labels)
            s.visual.params.labels = translated[cursor : cursor + n_labels]; cursor += n_labels
            n_steps = len(s.visual.params.steps)
            s.visual.params.steps = translated[cursor : cursor + n_steps]; cursor += n_steps
        return localized
3.2 Dual-Engine Offline TTS (Kokoro-82M for EN/HI and MMS-TTS for KN/TA/TE)Your TTS subsystem bridges two distinct architectures (Kokoro-82M and Meta's MMS-TTS) that operate at different native sample rates:LanguageISO / Script TagPrimary Offline TTS EngineParams & Disk SizeNative Sample RateVoice / Seed ConfigurationLicenseEnglishen (eng_Latn)hexgrad/Kokoro-82M82M (~327 MB)24,000 Hzlang_code='a', voice='af_heart' or 'af_bella'Apache 2.0Hindihi (hin_Deva)hexgrad/Kokoro-82M + espeak-ngShares 82M weights24,000 Hzlang_code='h', voice='hf_alpha', 'hf_beta', 'hm_omega', or 'hm_psi'Apache 2.0Kannadakn (kan_Knda)facebook/mms-tts-kan (VitsModel)36.3M (~38 MB Q8 ONNX)16,000 Hztorch.manual_seed(42) prior to forward passCC-BY-NC 4.0Tamil (Bonus)ta (tam_Taml)facebook/mms-tts-tam (VitsModel)36.3M16,000 Hztorch.manual_seed(42) prior to forward passCC-BY-NC 4.0Telugu (Bonus)te (tel_Telu)facebook/mms-tts-tel (VitsModel)36.3M16,000 Hztorch.manual_seed(42) prior to forward passCC-BY-NC 4.0Indic Upgradehi/kn/ta/teai4bharat/indic-parler-tts (if approved)0.9B (~2.3 GB FP16 / ~4.5 GB FP32)44,100 HzGated repo; ~1.35s–6.6s/clip on RTX 5070 FP16Apache 2.0Tarun must enforce four implementation details in localization/tts_engine.py:Install espeak-ng for Kokoro Hindi & OOD Fallback: Kokoro-82M uses misaki for English G2P and falls back to espeak-ng (espeak-ng hi) for Hindi phonemization (lang_code='h'). Install espeak-ng at the OS level (sudo apt-get install -y espeak-ng or brew install espeak-ng). Also note from VOICES.md that Kokoro voices perform best on moderate utterance lengths (roughly 100–200 tokens) and can struggle on ultra-short strings (<10–20 tokens) or rush on long passages (>400 tokens)—another reason why keeping each scene's narration to 1–2 complete sentences (18–30 words) is optimal.Pre-Cache Kokoro Voice Packs Offline: By default, KModel and KPipeline fetch config.json, kokoro-v1_0.pth, and individual voicepack files (af_heart.pt, hf_alpha.pt) from Hugging Face on first use. Either mount a local weights directory (/weights/kokoro) or execute a warm-up synthesis call for every configured voice while Wi-Fi is still enabled so all voicepacks are cached on disk before setting HF_HUB_OFFLINE=1.Seed the Stochastic Duration Predictor in MMS-TTS: Meta's VitsModel incorporates a stochastic duration predictor that synthesizes varying speech rhythms and durations on each run unless a fixed seed is set. Always call torch.manual_seed(42) immediately before model(**inputs) so cached and live runs remain 100% deterministic.Standardize Sample Rates to 24,000 Hz: Kokoro-82M outputs 24,000 Hz waveforms, whereas MMS-TTS outputs 16,000 Hz waveforms. Upsample MMS-TTS outputs from 16,000 Hz to 24,000 Hz (a 3:2 ratio) and append a 0.35-second silence buffer to each scene before concatenating into a single master WAV file. Because Python releases the GIL during C++/CUDA forward passes and espeak-ng calls, you can also run scene synthesis across a ThreadPoolExecutor when synthesizing multi-scene lessons on multi-core CPUs.Python# localization/tts_engine.py
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
import torch
from kokoro import KPipeline
from transformers import VitsModel, AutoTokenizer

TARGET_SR = 24000
TAIL_PAD_SEC = 0.35

class OfflineTTSEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Preload Kokoro pipelines for American English ('a') and Hindi ('h')
        self.kokoro_en = KPipeline(lang_code='a')
        self.kokoro_hi = KPipeline(lang_code='h')
        # Preload MMS-TTS checkpoints for Kannada (and bonus Tamil/Telugu if downloaded)
        self.mms_models = {}
        self.mms_tokenizers = {}
        for code, repo in [("kn", "facebook/mms-tts-kan"), ("ta", "facebook/mms-tts-tam"), ("te", "facebook/mms-tts-tel")]:
            try:
                self.mms_tokenizers[code] = AutoTokenizer.from_pretrained(repo, local_files_only=True)
                self.mms_models[code] = VitsModel.from_pretrained(repo, local_files_only=True).to(self.device).eval()
            except Exception:
                pass

    def synthesize_scene(self, text: str, lang: str) -> tuple[np.ndarray, float]:
        if lang in ("en", "hi"):
            pipe = self.kokoro_en if lang == "en" else self.kokoro_hi
            voice = "af_heart" if lang == "en" else "hf_alpha"
            chunks = [audio for _, _, audio in pipe(text, voice=voice, speed=1.0) if audio is not None]
            wav = np.concatenate(chunks) if chunks else np.zeros(TARGET_SR, dtype=np.float32)
        else:
            tokenizer = self.mms_tokenizers[lang]
            model = self.mms_models[lang]
            inputs = tokenizer(text, return_tensors="pt").to(self.device)
            torch.manual_seed(42)  # Required for deterministic VITS duration prediction
            with torch.no_grad():
                out = model(**inputs).waveform.squeeze().cpu().numpy()
            # Upsample 16,000 Hz -> 24,000 Hz (3:2 ratio)
            wav = resample_poly(out, up=3, down=2).astype(np.float32)

        max_val = np.max(np.abs(wav))
        if max_val > 1e-4:
            wav = (wav / max_val) * 0.90
        pad = np.zeros(int(TAIL_PAD_SEC * TARGET_SR), dtype=np.float32)
        full_wav = np.concatenate([wav, pad])
        duration_sec = round(len(full_wav) / TARGET_SR, 3)
        return full_wav, duration_sec

    def synthesize_all_scenes(self, scenes: list, lang: str, out_wav_path: str) -> list[dict]:
        """Synthesize all scenes, write combined 24kHz WAV, and return exact timing manifest."""
        timing_manifest = []
        all_wavs = []
        cursor_sec = 0.0
        for s in scenes:
            wav, dur = self.synthesize_scene(s.narration, lang)
            all_wavs.append(wav)
            timing_manifest.append({
                "id": s.id,
                "start_sec": round(cursor_sec, 3),
                "end_sec": round(cursor_sec + dur, 3),
                "duration_sec": dur,
                "narration": s.narration,
                "visual": s.visual.model_dump(),
            })
            cursor_sec += dur
        master_wav = np.concatenate(all_wavs)
        sf.write(out_wav_path, master_wav, TARGET_SR)
        return timing_manifest
http://googleusercontent.com/visual_element_1python
# exporter/export_mp4.py
import math
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

FPS = 20

def render_and_mux_mp4(
    html_path: Path,
    timing_manifest: list[dict],
    lesson_title: str,
    audio_wav_path: Path,
    output_mp4_path: Path,
    progress_callback=None,
) -> Path:
    total_duration = timing_manifest[-1]["end_sec"]
    total_frames = math.ceil(total_duration * FPS)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "image2pipe",
        "-vcodec", "mjpeg",      # Use 'png' if page.screenshot(type='png')
        "-r", str(FPS),
        "-i", "-",               # Read video frames from stdin pipe
        "-i", str(audio_wav_path),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",   # Required for universal browser/QuickTime playback
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest",
        str(output_mp4_path),
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-gpu-vsync", "--font-render-hinting=none"])
        page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        page.goto(html_path.resolve().as_uri(), wait_until="load")
        page.evaluate("() => document.fonts.ready")
        page.evaluate(
            "([title, scenes]) => window.initLesson(title, scenes)",
            [lesson_title, timing_manifest],
        )

        for frame_idx in range(total_frames):
            t_sec = frame_idx / FPS
            page.evaluate(f"window.renderAtTime({t_sec:.4f})")
            frame_bytes = page.screenshot(type="jpeg", quality=92)
            proc.stdin.write(frame_bytes)
            if progress_callback and frame_idx % 20 == 0:
                progress_callback(int((frame_idx / total_frames) * 100))

        browser.close()

    proc.stdin.close()
    _, stderr = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg mux failed: {stderr.decode('utf-8', errors='ignore')}")
    if progress_callback:
        progress_callback(100)
    return output_mp4_path
5.2 Two-Level Caching by (topic, language)Implement a two-tier disk cache keyed by normalized topic (topic.strip().lower()):Tier 1 — English LessonPlan Cache (cache/plans/{topic_slug}.json): Because plan_lesson() always plans in English (language_neutral: true), when a judge views a concept in English and then requests the same concept in Kannada or Hindi, the orchestrator loads the validated English LessonPlan directly from Tier 1 cache in <2 ms, bypassing the 3B LLM completely and jumping straight to IndicTrans2 and TTS.Tier 2 — Rendered Artifact Cache (cache/artifacts/{topic_slug}_{lang}/): Store manifest.json, lesson_audio.wav, and lesson.mp4 keyed by (topic_slug, lang). Any repeated query for a previously generated (topic, language) pair serves the browser preview and MP4 download immediately.5.3 Mandatory Open-Source Licenses and Attribution Table for README.mdInclude this table in README.md to satisfy the engineering and licensing criteria:Component / ArtifactModel ID / PackageRole in PipelineLicenseCompliance & Attribution NotesLLM Plannerllama3.2:3b, qwen3:4b, or gemma4:e4b via OllamaEnglish JSON curriculum planningLlama 3.2 Community / Apache 2.0 (qwen3)Executed locally via Ollama daemon; no external API calls.Indic Translationai4bharat/indictrans2-en-indic-dist-200M + IndicTransToolkitEnglish to Hindi, Kannada, Tamil, Telugu translationMIT LicensePermissive open-source license; includes Cython IndicProcessor.EN & HI TTShexgrad/Kokoro-82M + misaki + espeak-ng24 kHz speech synthesis for English & HindiApache 2.0 (Kokoro-82M)Trained exclusively on permissive/non-copyrighted audio and IPA labels.KN / TA / TE TTSfacebook/mms-tts-kan, mms-tts-tam, mms-tts-tel16 kHz VITS speech synthesis for Kannada, Tamil, TeluguCC-BY-NC 4.0Non-commercial research/hackathon license; swap with ai4bharat/indic-parler-tts (Apache 2.0) for commercial deployment.Indic TypographyNoto Sans, Noto Sans Kannada, Noto Sans Devanagari, Noto Sans Tamil, Noto Sans TeluguOffline script rendering & ligature shaping in ChromiumSIL Open Font License 1.1Bundled locally in renderer/assets/fonts/; zero CDN calls.Video & Web StackPlaywright (Chromium), FFmpeg (libx264), FastAPI, PydanticDeterministic frame capture, MP4 muxing, schema validationApache 2.0 / MIT / GPLv2+ (libx264)Invoked locally via Python subprocess.Popen pipes.6. Hour-by-Hour Execution Schedule and Wi-Fi-Off Verification Checklist6.1 Synchronized Team Milestones (From Hour 1.5 to 06:00 Freeze)DeadlineTarget MilestoneYour Deliverable (Orchestrator)Farhan's Deliverable (Visuals)Tarun's Deliverable (TTS/Indic)Ayush's Deliverable (Export/UI)11:00 (Now + 15m)Schema & Repo LockCommit CLAUDE.md, schema.py, and golden_ohms_law.json.Initialize player.html (1280x720 canvas) reading golden_ohms_law.json.Verify local weights for Kokoro-82M, mms-tts-kan, and indictrans2-200M.Scaffold export_mp4.py (image2pipe) and FastAPI skeleton.14:00 (Hour 5 Gate)Hardcoded English E2ECLI script wiring golden_ohms_law.json → TTS → Exporter.5 core templates (title, compare, equation, flow, bullets) working in renderAtTime(t).Kokoro-82M (lang_code='a') generating 24 kHz WAV + timing_manifest.Playwright + FFmpeg exporting playable ohms_law_en.mp4 + browser preview.18:00Live LLM + HI & KNLive Ollama planner (think=False, format=schema) + 1-retry + fallback.Smooth cubic easing transitions + auto-scaling text for longer Indic strings.IndicTrans2 + IndicProcessor batching + Kokoro ('h') & mms-tts-kan ('kn') + Noto fonts.Language selector (EN, HI, KN), progress bar, and (topic, lang) cache.22:008 Templates + PolishTune few-shot prompts so all 8 visual types are selected appropriately; verify word-count bounds.Complete remaining 3 templates (labeled_diagram, graph, timeline) + visual polish.Progressive word-highlight caption bar + symbol/number sanitizer for Kannada VITS.Add bonus Tamil/Telugu (mms-tts-tam/tel) + UI error boundary toasts.Overnight (22:00–05:30)20-Topic Stress TestRun test_harness.py across 20 random STEM/general topics; inspect and fix edge cases.Fix any label clipping or layout overlap spotted in the 20 exported MP4s.Verify zero Devanagari script leakage or missing glyphs in HI and KN.Log P50/P90 generation latencies and finalize README.md + licenses table.06:00 OnwardFeature Freeze & RehearsalPre-warm Ollama (keep_alive=-1) and pre-cache 10 likely demo topics.Freeze engine.js and templates.js; no layout changes after 06:00.Check speaker audio normalization in offline mode.Disable Wi-Fi at OS level; rehearse the live judge flow twice from a cold browser tab.6.2 Overnight 20-Topic Automated Stress Harness (exporter/test_harness.py)Run an automated batch script overnight across 20 varied topics (such as Photosynthesis, Newton's Third Law, Binary Search, Supply and Demand, DNA Replication, Pythagoras Theorem, Water Cycle, Compound Interest, Acid-Base Titration, and TCP Three-Way Handshake). For each topic and language (en, hi, kn), assert five automated checks:plan_lesson(topic) returns a valid LessonPlan with 4 to 6 scenes and fallback_used == False on at least 19 of 20 topics.Total audio duration (timing_manifest[-1]["end_sec"]) lands strictly between 30.0 and 90.0 seconds.For lang == "kn", every scene's translated narration contains Unicode characters in the Kannada block (U+0C80–U+0CFF) and zero characters in the Devanagari block (U+0900–U+097F), confirming IndicProcessor.postprocess_batch() executed properly.output_mp4_path.exists() and file size exceeds 150,000 bytes.ffprobe confirms valid h264 (yuv420p) video and aac audio streams whose duration matches timing_manifest[-1]["end_sec"] within ±0.2 seconds.6.3 Pre-Demo Air-Gap Verification Checklist (Run at 17:30 Today and 06:00 Tomorrow)Export Offline Flags in Startup Script: Add export HF_HUB_OFFLINE=1 and export TRANSFORMERS_OFFLINE=1 at the top of run_demo.sh so neither Hugging Face Hub nor Transformers attempts a network metadata check when Wi-Fi is off.Pre-Trigger Every Kokoro Voice File: Because Kokoro-82M downloads voice .pt files lazily on first use, run one synthesis call for af_heart, af_bella, hf_alpha, and hm_omega while still on Wi-Fi so all .pt voicepacks are stored in the local Hugging Face cache.Execute Two Full Rehearsals with Wi-Fi Off: Turn off Wi-Fi at the OS level, start the server (which calls warm_up_ollama() and loads IndicTrans2, Kokoro-82M, and mms-tts-kan into memory), and run two completely uncached topics chosen by a teammate in English, Hindi, and Kannada through browser playback and MP4 download.