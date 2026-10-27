# orchestrator/fallbacks.py
from orchestrator.schema import NOT_SPOKEN, WORDS_MAX, WORDS_MIN, LessonPlan, scenes_for, word_band
from orchestrator.spoken import to_spoken

MAX_CONCEPT_WORDS = 4
MAX_CONCEPT_CHARS = 40

# Spoken-only filler used to reach the requested length; each is a complete, topic-neutral sentence.
# Unique sentences ensure zero repeated lines across scenes.
PADS = (
    "Keep this picture in mind while you revise.",
    "Notice how each step follows the one before it.",
    "Think of one example you have seen yourself.",
    "This idea matters in everyday life.",
    "Every part of the system works together smoothly.",
    "Understanding the foundation makes advanced concepts much easier.",
    "Take a moment to connect these ideas.",
    "Consistent practice strengthens your intuition over time.",
    "Observing real patterns confirms theoretical reasoning.",
    "Clear reasoning eliminates confusion during complex problem solving.",
    "Step by step analysis reveals how each component interacts.",
    "Careful observation helps uncover subtle connections.",
    "Simple models often explain surprisingly complex phenomena.",
    "Structured thinking makes challenging problems manageable.",
    "Reliable systems depend on well understood principles.",
    "Check your work.",
    "Think about it.",
    "Keep it simple.",
    "That is the rule.",
    "Try one example.",
    "Remember the core rule.",
    "Focus on the big picture.",
    "Practice makes it clear.",
    "Test every assumption.",
    "Verify each step.",
)


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


def build_safe_fallback_lesson(concept: str, level: str = "beginner", target_sec: int = 60) -> LessonPlan:
    """A deterministic, schema-valid lesson for any concept, sized to the requested length (CC-2).

    Used only when every planner rung failed, so it must satisfy the same budget the schema enforces. Every scene
    is a short core sentence plus whole neutral sentences, added or dropped one at a time until the lesson's
    estimated audio sits inside the requested band.
    """
    c = _short_concept(concept)  # shown on screen: labels, steps, title
    s = _spoken(c)  # read aloud: narration
    cores = [
        (f"How does {s} actually work in everyday life?",
         {"type": "title", "params": {"labels": [c, "Core Principles & Overview", "Interactive Study Guide"],
                                      "steps": [f"Mastering {c} Step by Step"]}}),
        (f"Comparing key aspects of {s} clarifies how different components behave under standard conditions.",
         {"type": "table", "params": {"labels": ["Feature", "Input Factor", "Observed Outcome", "Primary Purpose"],
                                      "steps": ["Primary State: Baseline condition", "Active Process: Dynamic change", "Final State: Balanced system"]}}),
        (f"At its core, {s} takes an input, applies one clear rule, and produces a verified output.",
         {"type": "flow", "params": {"labels": ["1. Initial Input", f"2. Apply {c} Transformation", "3. Verified Result"],
                                     "steps": ["Deterministic execution through every stage"]}}),
        (f"Looking at how {s} divides across components reveals the relative balance within the system.",
         {"type": "pie", "params": {"labels": ["Primary Share: 50 percent", "Secondary Share: 30 percent", "Remaining Share: 20 percent"],
                                    "steps": ["Balanced distribution across components"]}}),
        (f"To recap {s}: remember the core rule, follow the process flow, and verify each stage.",
         {"type": "bullets", "params": {"labels": [f"Key Takeaways: {c}"],
                                        "steps": ["Observe foundational principles in action",
                                                  "Follow the step-by-step transformation flow",
                                                  "Confirm each result with systematic verification"]}}),
        ("A common mistake is skipping verification and assuming outcomes without checking.",
         {"type": "compare", "params": {"labels": ["Common Pitfall", "Recommended Practice"],
                                        "steps": ["Unchecked assumptions cause failure", "Systematic validation ensures reliability"]}}),
    ]
    count = scenes_for(target_sec)
    keep = {4: (0, 1, 2, 4), 5: (0, 1, 2, 3, 4), 6: (0, 1, 2, 3, 5, 4)}[count]
    narrations = [cores[i][0] for i in keep]
    visuals = [cores[i][1] for i in keep]

    lo, hi = word_band(target_sec, count)
    added: list[list[str]] = [[] for _ in range(count)]

    def text_of(i: int) -> str:
        return " ".join([narrations[i]] + added[i])

    def total() -> int:
        return sum(len(text_of(i).split()) for i in range(count))

    def can_add(i: int, pad: str) -> bool:
        return len(text_of(i).split()) + len(pad.split()) <= WORDS_MAX

    def grow_until(limit: int) -> None:
        for _ in range(1000):
            if total() >= limit:
                return
            progress = False
            for i in sorted(range(count), key=lambda j: len(text_of(j).split())):
                used = {p for sp in added for p in sp}
                for pad in PADS:
                    if pad not in used and can_add(i, pad):
                        added[i].append(pad)
                        progress = True
                        break
                if total() >= limit:
                    return
            if not progress:
                return

    middle = (lo + hi) // 2
    grow_until(middle)
    while total() > hi:
        i = max(range(count), key=lambda j: len(text_of(j).split()))
        if not added[i]:
            break
        added[i].pop()
    grow_until(lo)

    scenes = []
    for i in range(count):
        text = " ".join([narrations[i]] + added[i])
        scenes.append({"id": i + 1, "narration": text, "visual": visuals[i], "caption_key": "narration"})
    return LessonPlan(title=f"Understanding {c}: Core Principles & Application", language_neutral=True,
                      level=level, target_sec=target_sec, scenes=scenes)
