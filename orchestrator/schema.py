# orchestrator/schema.py
# One rule per layer:
#   JSON schema (Ollama grammar) -> shape, enums, list sizes, hard char cap on narration
#   SceneSpec validator          -> per-scene word count, spoken words only
#   LessonPlan validator         -> lesson word total and estimated audio length
#   pipeline.duration_gate       -> real measured audio length after TTS
#   mathcheck.verify_plan        -> worked-example arithmetic (check.expr vs check.result), before to_spoken
#   VisualSpec validator         -> code_walkthrough carries code + trace, every other type carries neither
import re
import unicodedata
from math import ceil, floor
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

WORDS_MIN, WORDS_MAX = 14, 32
TOTAL_MIN, TOTAL_MAX = 85, 150  # historical default band; the live budget follows target_sec (CC-2)
SPEECH_WPS, TAIL = 2.3, 0.35
EST_SEC_MIN, EST_SEC_MAX = 35, 85
NOT_SPOKEN = re.compile(r"[0-9=×÷+<>%Ω/\\°√π]")  # matched after NFKC, so CO₂ and km² count as digits

# CC-2: a lesson's length is a request, not a constant. Scene count and word budget follow target_sec so the
# planner can fill 30 s or 90 s honestly; duration_gate() still enforces the real 30-90 s window after TTS.
SCENE_STEPS = ((35, 4), (70, 5), (90, 6))


def scenes_for(target_sec: int) -> int:
    """How many scenes a lesson of this length should have (4 short, 5 medium, 6 long)."""
    for limit, count in SCENE_STEPS:
        if target_sec <= limit:
            return count
    return SCENE_STEPS[-1][1]


def word_budget(target_sec: int, scenes: int) -> int:
    """Words that fill target_sec once every scene carries its 0.35 s tail."""
    return max(0, round((target_sec - TAIL * scenes) * SPEECH_WPS))


def sec_band(target_sec: int) -> tuple[float, float]:
    """The estimated-audio window a plan must land in: +/-15% of the request, inside the 30-90 s product bound."""
    return max(30.0, target_sec * 0.85), min(90.0, target_sec * 1.15)


def accept_band(target_sec: int) -> tuple[float, float]:
    """What the validator accepts. The prompt still asks for sec_band(); a real lesson that comes in short (down to
    60% of the request, never under 30 s) beats the topic-agnostic safe template it would otherwise turn into."""
    return max(30.0, target_sec * 0.6), sec_band(target_sec)[1]


def word_band(target_sec: int, scenes: int) -> tuple[int, int]:
    """The word counts that put the estimate inside sec_band(), also bounded by the 14-32 words per scene rule."""
    lo_sec, hi_sec = sec_band(target_sec)
    lo = max(WORDS_MIN * scenes, ceil((lo_sec - TAIL * scenes) * SPEECH_WPS))
    hi = min(WORDS_MAX * scenes, floor((hi_sec - TAIL * scenes) * SPEECH_WPS))
    return lo, hi


def estimated_sec(words: int, scenes: int) -> float:
    return words / SPEECH_WPS + TAIL * scenes

CODE_MAX_LINES, CODE_LINE_CHARS, TRACE_MAX_STEPS = 12, 80, 6

VisualType = Literal[
    "flow", "bullets", "equation", "labeled_diagram",
    "graph", "timeline", "compare", "title", "code_walkthrough"
]

class VarState(BaseModel):
    name: str = Field(..., min_length=1, max_length=24, description="Variable name, e.g. i")
    value: str = Field(..., min_length=1, max_length=24, description="Its value after this line runs, e.g. 0")

class CodeStep(BaseModel):
    line: int = Field(..., ge=1, le=CODE_MAX_LINES,
                      description="1-based index into params.code: the line highlighted at this step.")
    vars: List[VarState] = Field(default_factory=list, max_length=4,
                                 description="The variable state table at this step.")

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
    # code_walkthrough only. code and vars are DATA: the renderer draws them as text and nothing here is
    # ever eval'd, exec'd, compiled or run in a subprocess. The planner writes this, so it is untrusted
    # input, the same stance mathcheck.py takes when it evaluates check.expr through an AST whitelist.
    code: List[str] = Field(
        default_factory=list,
        max_length=CODE_MAX_LINES,
        description="code_walkthrough only: source lines, drawn verbatim. Never executed."
    )
    trace: List[CodeStep] = Field(
        default_factory=list,
        max_length=TRACE_MAX_STEPS,
        description="code_walkthrough only: ordered steps; each highlights one line and shows the variables."
    )

    @field_validator("code")
    @classmethod
    def check_code_lines(cls, v: List[str]) -> List[str]:
        for i, line in enumerate(v, 1):
            if len(line) > CODE_LINE_CHARS:
                raise ValueError(f"code line {i} is {len(line)} chars, max {CODE_LINE_CHARS}")
        return v

class VisualSpec(BaseModel):
    type: VisualType
    params: VisualParams

    @model_validator(mode="after")
    def check_code_walkthrough(self) -> "VisualSpec":
        if self.type == "code_walkthrough":
            if not self.params.code:
                raise ValueError(f"code_walkthrough needs visual.params.code: 1 to {CODE_MAX_LINES} source lines")
            if not self.params.trace:
                raise ValueError(f"code_walkthrough needs visual.params.trace: 1 to {TRACE_MAX_STEPS} steps")
            n = len(self.params.code)
            for st in self.params.trace:
                if st.line > n:
                    raise ValueError(f"trace line {st.line} is past the end of code ({n} lines)")
        elif self.params.code or self.params.trace:
            raise ValueError(f"code and trace belong to code_walkthrough only, not {self.type!r}")
        return self

class Check(BaseModel):
    expr: str = Field(..., max_length=60, description="Arithmetic only: numbers, + - * / ** and parentheses. E.g. 230 / 46")
    result: str = Field(..., max_length=30, description="The answer the narration states, e.g. 5")

class SceneSpec(BaseModel):
    id: int = Field(..., ge=1, le=6)
    narration: str = Field(
        ...,
        min_length=1,
        max_length=320,
        description="1-2 short spoken sentences (18-30 words). Spoken words only: numbers written as words, no digits or symbols."
    )
    visual: VisualSpec
    caption_key: Literal["narration"] = "narration"
    check: Optional[Check] = None  # only on a numeric worked example; absent everywhere else

    @field_validator("narration")
    @classmethod
    def check_spoken_narration(cls, v: str) -> str:
        v = v.strip()
        n = len(v.split())
        if not WORDS_MIN <= n <= WORDS_MAX:
            raise ValueError(f"narration must be {WORDS_MIN}-{WORDS_MAX} words, got {n}")
        if NOT_SPOKEN.search(unicodedata.normalize("NFKC", v)):
            raise ValueError("narration must be spoken words only: no digits or symbols "
                             "(write carbon dioxide, square kilometres, degrees in words)")
        return v

class LessonPlan(BaseModel):
    title: str = Field(..., min_length=3, max_length=90)
    language_neutral: bool = True
    level: Literal["beginner", "intermediate"] = "beginner"
    target_sec: int = Field(60, ge=30, le=90)
    scenes: List[SceneSpec] = Field(..., min_length=4, max_length=6)

    @model_validator(mode="after")
    def check_total(self) -> "LessonPlan":
        words = sum(len(s.narration.split()) for s in self.scenes)
        est = estimated_sec(words, len(self.scenes))
        lo, hi = accept_band(self.target_sec)
        if not (lo <= est <= hi):
            raise ValueError(
                f"total {words} words (~{est:.0f}s) does not fill a {self.target_sec}s lesson: "
                f"aim for {lo:.0f}-{hi:.0f}s of audio across {len(self.scenes)} scenes"
            )
        return self
