# orchestrator/fallbacks.py
from orchestrator.schema import NOT_SPOKEN, LessonPlan
from orchestrator.spoken import to_spoken

MAX_CONCEPT_WORDS = 4
MAX_CONCEPT_CHARS = 40


def _short_concept(concept: str) -> str:
    """Clamp the concept so every templated narration stays inside the per-scene word and char limits."""
    words = concept.strip().split()[:MAX_CONCEPT_WORDS]
    c = " ".join(w[:1].upper() + w[1:] for w in words)  # keep acronyms like DNA intact
    if len(c) > MAX_CONCEPT_CHARS:
        c = c[:MAX_CONCEPT_CHARS].rstrip()
    return c or "This Topic"


def _spoken(c: str) -> str:
    """Spoken form of the concept for narration: "Web 3.0" -> "Web three point zero", "TCP/IP" -> "TCP IP"."""
    c = to_spoken(c.replace("/", " "))  # in a name, "/" separates terms rather than dividing
    c = NOT_SPOKEN.sub(" ", c)  # anything the schema still rejects
    return " ".join(c.split()[:MAX_CONCEPT_WORDS]) or "This Topic"


def build_safe_fallback_lesson(concept: str) -> LessonPlan:
    c = _short_concept(concept)  # shown on screen: labels, steps, title
    s = _spoken(c)  # read aloud: narration
    return LessonPlan(
        title=f"Understanding {c}: Core Principles & Application",
        language_neutral=True,
        scenes=[
            {"id": 1, "narration": f"Have you ever wondered how {s} works in everyday Indian technology and why engineers and scientists rely on it daily?", "visual": {"type": "title", "params": {"labels": [c, "Core Concept & Intuition", "Step-by-Step Guide"], "steps": [f"Mastering {c} in One Minute"]}}, "caption_key": "narration"},
            {"id": 2, "narration": f"Think of {s} like organizing traffic at a busy Bengaluru junction: clear rules transform chaotic inputs into smooth, predictable outcomes.", "visual": {"type": "compare", "params": {"labels": [f"Without {c}", f"With {c}"], "steps": ["Unstructured & slow process", "Systematic & predictable result"]}}, "caption_key": "narration"},
            {"id": 3, "narration": f"At its core, {s} operates through three connected stages: receiving the input state, applying the governing transformation, and producing the verified output.", "visual": {"type": "flow", "params": {"labels": ["1. Input State", f"2. Apply {c} Rule", "3. Verified Output"], "steps": ["Deterministic transformation at each stage"]}}, "caption_key": "narration"},
            {"id": 4, "narration": f"In a practical example of {s}, when we change the primary input parameter, the output responds proportionally according to the system constraints.", "visual": {"type": "labeled_diagram", "params": {"labels": [f"{c} System", "Input Parameter", "Control Mechanism", "Measured Output"], "steps": ["Step 1: Measure input", "Step 2: Compute response"]}}, "caption_key": "narration"},
            {"id": 5, "narration": f"To recap {s}: remember the core mechanism, trace how inputs map to outputs, and apply this mental model to real-world problems.", "visual": {"type": "bullets", "params": {"labels": [f"Key Takeaways: {c}"], "steps": ["Understand the intuitive analogy", "Follow the three-step input-to-output flow", "Verify results with a concrete example"]}}, "caption_key": "narration"},
        ],
    )
