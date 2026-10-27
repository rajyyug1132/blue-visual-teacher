# orchestrator/prompts.py
import json

from orchestrator.schema import WORDS_MAX, WORDS_MIN, scenes_for, word_band

SYSTEM_PROMPT = """You are an expert Indian STEM educator and visual curriculum planner.
Given a student's concept, output ONLY valid JSON matching the LessonPlan schema. Never output code or markdown.

MANDATORY PEDAGOGICAL STRUCTURE (the request states how many scenes your lesson has; keep this order):
- Scene 1 (Hook): A relatable everyday Indian question or phenomenon (18-26 words, target 18-30). Visual type: "title".
- Scene 2 (Intuition / Analogy): A concrete physical analogy or comparison from daily life in India—water tanks, cricket, IRCTC trains, UPI, traffic, or kitchen cooking (20-28 words). Visual type: "compare", "table", or "labeled_diagram".
- Scene 3 (Core Principle / Mechanism): State the exact scientific, mathematical, or conceptual rule clearly (20-28 words). Visual type: "flow", "equation", or "pie".
- Scene 4 (Worked Example): Walk through ONE concrete numerical or step-by-step example from start to finish (22-30 words). Visual type: "flow", "table", or "labeled_diagram".
- Scene 5 (Recap): Summarize the 3 essential takeaways so the student remembers the rule (18-25 words). Visual type: "bullets".

STRICT RULES:
1. Plan in clear, simple English ("language_neutral": true).
2. Each scene's "narration" MUST be 8-42 spoken words (target 18-30 words). The request states the total word budget for its lesson length: obey it exactly, because total audio duration must land between 30.0 and 90.0 seconds.
3. "narration" is spoken words only, read aloud by a voice engine. Write every number in words ("two hundred thirty", not "230") and every operator in words ("V equals I times R", "fifty percent"). Never put digits or symbols (0-9 = × ÷ + / % Ω < >) in narration; keep figures and formulas ("230 V", "V = I × R") in visual.params.labels and visual.params.steps.
4. Keep visual.params.labels (2-4 items) and visual.params.steps (1-4 items) under 6 words each so they translate cleanly into Hindi and Kannada without overflowing the canvas.
5. STRICT VISUAL QUOTA: Visual types must be selected from: "title", "labeled_diagram", "flow", "pie", "table", "compare", "equation", "bullets".
   - Max 3 diagram scenes: At most 3 scenes in a lesson can use illustrative/diagram types ("labeled_diagram" or "title").
   - Mandatory structured charts: At least 2 scenes in every 5-scene lesson MUST use structured data visuals ("flow", "pie", "table", "compare", or "bullets").
6. ZERO LINE REPETITION GUARDRAIL:
   - Every scene must explain a distinct aspect of the concept. Never repeat sentences across scenes (no two scenes may share >60% word overlap).
   - In each scene, labels and steps must be unique strings and must NEVER be a verbatim copy of the scene's narration.
7. NUMBER POLICY. Every request states one.
   - "checked" (topic with a standard formula): scene 4 uses one or two arithmetic steps with whole numbers below 10,000 and adds "check": {"expr": "<numbers and + - * / ** ( ) only>", "result": "<the answer>"}, e.g. {"expr": "230 / 46", "result": "5"}. Every number anywhere in the lesson must come from that calculation; small counts up to ten are fine. Scene 4's narration must say the final answer in words.
   - "none" (descriptive topic): no quantities at all. No digits, no number words above ten, no units of measurement and no "=" in narration, labels or steps. Describe what happens and why, not how much. Years are dates, not quantities, so they are allowed: four digits in labels, spoken as words in narration ("nineteen forty-seven"). Scene 4 walks through the steps in words. Omit "check".
"""

CLASSIFY_PROMPT = (
    'Does the concept "{concept}" have a standard mathematical, physics, chemistry or finance formula that a '
    "worked numerical example can use? true for topics like Ohm's Law, Compound Interest, Pythagoras Theorem, "
    "Speed Distance Time. false for descriptive or process topics like Monsoon, Mughal Empire, Photosynthesis, "
    'Democracy, TCP Handshake. Reply as JSON: {{"has_formula": true}} or {{"has_formula": false}}.'
)

QUALITATIVE_MODE = ("QUALITATIVE MODE: explain this concept without any quantities. No digits, no number words "
                    "above ten, no units of measurement, no formulas and no '=' anywhere; years are allowed. "
                    "Describe what happens and why, in natural sentences. Scene 4 walks through the steps in words.")


LEVEL_NOTES = {
    "beginner": "everyday words and short sentences; define each new term the first time it appears; keep one concrete analogy",
    "intermediate": "precise terminology; state the rule and when it applies; assume the basics are already known",
}


def request(concept: str, policy: str, level: str = "beginner", target_sec: int = 60) -> str:
    """The user turn for one concept; few-shots use the same shape so the policy line is learned by example.

    level and target_sec are Stage 1 inputs (CC-2): the level shapes vocabulary and depth only, the length shapes
    the scene count and the word budget the schema will hold the plan to.
    """
    scenes = scenes_for(target_sec)
    lo, hi = word_band(target_sec, scenes)
    per_lo, per_hi = max(WORDS_MIN, -(-lo // scenes)), min(WORDS_MAX, -(-hi // scenes))
    return (f"Concept: {concept.strip()}\n"
            f"Number policy: {policy}\n"
            f"Learner level: {level} -- {LEVEL_NOTES.get(level, LEVEL_NOTES['beginner'])}.\n"
            f"Lesson length: {target_sec} seconds -- write exactly {scenes} scenes, {lo}-{hi} words in total "
            f"({per_lo}-{per_hi} words per scene).")

BINARY_SEARCH_QUALITATIVE = {  # few-shot for policy "none": an algorithm explained with no quantities
    "title": "Binary Search: Halving the Search Space",
    "language_neutral": True,
    "scenes": [
        {"id": 1, "narration": "How does a railway clerk find one passenger's booking among a huge pile of sorted records without checking every single entry one by one?",
         "visual": {"type": "title", "params": {"labels": ["Binary Search", "Logarithmic Time", "Divide and Conquer"], "steps": ["Fast Lookup in Sorted Data"]}}, "caption_key": "narration"},
        {"id": 2, "narration": "Imagine finding a roll number in a sorted exam sheet. Instead of reading from the top, open the exact middle page and throw away half instantly.",
         "visual": {"type": "compare", "params": {"labels": ["Linear Scan: One by One", "Binary Search: Cut in Half"], "steps": ["Linear: work grows with the list", "Binary: work grows very slowly"]}}, "caption_key": "narration"},
        {"id": 3, "narration": "Binary Search compares your target with the middle element. If the target is larger, discard the left half; if smaller, discard the right half.",
         "visual": {"type": "flow", "params": {"labels": ["Find the middle element", "Compare target with middle", "Keep the correct half"], "steps": ["Requires a sorted list", "Halves the search each step"]}}, "caption_key": "narration"},
        {"id": 4, "narration": "Let's search a sorted list for a target. We check the middle item, see the target is larger, keep only the right half, and find it on the next check.",
         "visual": {"type": "labeled_diagram", "params": {"labels": ["Sorted list of roll numbers", "Check middle: too small", "Keep the right half", "Target found"], "steps": ["Two checks instead of many"]}}, "caption_key": "narration"},
        {"id": 5, "narration": "To recap: Binary Search needs sorted data, checks the middle each step, and finishes in logarithmic time, even for very long lists.",
         "visual": {"type": "bullets", "params": {"labels": ["Binary Search Summary"], "steps": ["Precondition: data must be sorted", "Mechanism: halve the range each step", "Speed: logarithmic comparisons"]}}, "caption_key": "narration"},
    ],
}

FEW_SHOT_MESSAGES = [
    {"role": "user", "content": request("Ohm's Law", "checked")},
    {"role": "assistant", "content": '{"title":"Ohm\'s Law: Voltage, Current, and Resistance","language_neutral":true,"scenes":[{"id":1,"narration":"Why does your phone charger get warm while fast-charging, or a ceiling fan slow down when voltage drops during summer in Bengaluru?","visual":{"type":"title","params":{"labels":["Ohm\'s Law","V = I × R","Voltage, Current & Resistance"],"steps":["Everyday Electricity in India"]}},"caption_key":"narration"},{"id":2,"narration":"Think of an overhead water tank on your house roof. Water height is Voltage, water flow through the pipe is Current, and a narrow tap is Resistance.","visual":{"type":"compare","params":{"labels":["Roof Tank Height → Voltage (V)","Pipe Water Flow → Current (I)","Narrow Tap → Resistance (R)"],"steps":["Higher pressure pushes more flow","Narrower pipe restricts flow"]}},"caption_key":"narration"},{"id":3,"narration":"Georg Ohm discovered that Voltage equals Current multiplied by Resistance: V equals I times R. Doubling voltage doubles the current if resistance stays constant.","visual":{"type":"equation","params":{"labels":["V = I × R","V : Voltage (Volts)","I : Current (Amperes)","R : Resistance (Ohms Ω)"],"steps":["I = V / R","R = V / I"]}},"caption_key":"narration"},{"id":4,"narration":"Let\'s test a two hundred thirty volt Indian wall socket powering an iron box with forty-six ohms resistance. Two hundred thirty divided by forty-six gives five amperes of current.","visual":{"type":"flow","params":{"labels":["Supply: V = 230 V","Heater Coil: R = 46 Ω","Formula: I = V / R","Result: I = 5 A"],"steps":["230 V ÷ 46 Ω = 5 Amperes"]}},"caption_key":"narration","check":{"expr":"230 / 46","result":"5"}},{"id":5,"narration":"To recap: Voltage pushes electrons, Resistance opposes them, and Current is the resulting flow governed by V equals I times R.","visual":{"type":"bullets","params":{"labels":["Key Takeaways: Ohm\'s Law"],"steps":["Voltage (V): Electrical pressure in Volts","Resistance (R): Opposition to flow in Ohms (Ω)","Current (I = V / R): Flow rate in Amperes"]}},"caption_key":"narration"}]}'},
    {"role": "user", "content": request("Binary Search", "none")},
    {"role": "assistant", "content": json.dumps(BINARY_SEARCH_QUALITATIVE, ensure_ascii=False, separators=(",", ":"))},
]
