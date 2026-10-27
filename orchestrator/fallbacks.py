# orchestrator/fallbacks.py
from orchestrator.schema import NOT_SPOKEN, WORDS_MAX, WORDS_MIN, LessonPlan, scenes_for, word_band
from orchestrator.spoken import to_spoken

MAX_CONCEPT_WORDS = 4
MAX_CONCEPT_CHARS = 40

# Spoken-only filler used to reach the requested length; each is a complete, topic-neutral sentence. The short
# ones exist so a scene can be topped up to the per-scene cap without overshooting it.
PADS = (
    "Keep this picture in mind while you revise.",
    "Notice how each step follows the one before it.",
    "Think of one example you have seen yourself.",
    "This idea matters in everyday life.",
    "Check your work.",
    "Think about it.",
    "Keep it simple.",
    "That is the rule.",
    "Try one example.",
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
         {"type": "title", "params": {"labels": [c, "Core Concept & Intuition", "Step-by-Step Guide"],
                                      "steps": [f"Mastering {c} in One Minute"]}}),
        (f"Think of {s} like traffic rules at a busy junction: clear rules turn chaos into predictable flow.",
         {"type": "compare", "params": {"labels": [f"Without {c}", f"With {c}"],
                                        "steps": ["Unstructured & slow process", "Systematic & predictable result"]}}),
        (f"At its core, {s} takes an input, applies one clear rule, and produces a verified output.",
         {"type": "flow", "params": {"labels": ["1. Input State", f"2. Apply {c} Rule", "3. Verified Output"],
                                     "steps": ["Deterministic transformation at each stage"]}}),
        (f"In practice, we change one input to {s} and watch how the output responds.",
         {"type": "labeled_diagram", "params": {"labels": [f"{c} System", "Input Parameter", "Control Mechanism",
                                                           "Measured Output"],
                                                "steps": ["Step 1: Measure input", "Step 2: Compute response"]}}),
        ("A common mistake is skipping a check and trusting the first result.",
         {"type": "compare", "params": {"labels": ["Common Mistake", "Correct Approach"],
                                        "steps": ["Skip the check", "Verify each input"]}}),
        (f"To recap {s}: remember the rule, follow the input to output, and verify with an example.",
         {"type": "bullets", "params": {"labels": [f"Key Takeaways: {c}"],
                                        "steps": ["Understand the intuitive analogy",
                                                  "Follow the three-step input-to-output flow",
                                                  "Verify results with a concrete example"]}}),
    ]
    count = scenes_for(target_sec)
    keep = {4: (0, 1, 2, 3), 5: (0, 1, 2, 3, 5), 6: (0, 1, 2, 3, 4, 5)}[count]
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
                for pad in PADS:
                    if pad not in added[i] and can_add(i, pad):
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
