# orchestrator/schema.py
# One rule per layer:
#   JSON schema (Ollama grammar) -> shape, enums, list sizes, hard char cap on narration
#   SceneSpec validator          -> per-scene word count, spoken words only
#   LessonPlan validator         -> lesson word total and estimated audio length
#   pipeline.duration_gate       -> real measured audio length after TTS
#   mathcheck.verify_plan        -> worked-example arithmetic (check.expr vs check.result), before to_spoken
import re
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

WORDS_MIN, WORDS_MAX = 14, 32
TOTAL_MIN, TOTAL_MAX = 85, 150
SPEECH_WPS, TAIL = 2.3, 0.35
EST_SEC_MIN, EST_SEC_MAX = 35, 85
NOT_SPOKEN = re.compile(r"[0-9=×÷+<>%Ω/\\]")

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
        if NOT_SPOKEN.search(v):
            raise ValueError("narration must be spoken words only: no digits or symbols")
        return v

class LessonPlan(BaseModel):
    title: str = Field(..., min_length=3, max_length=90)
    language_neutral: bool = True
    scenes: List[SceneSpec] = Field(..., min_length=4, max_length=6)

    @model_validator(mode="after")
    def check_total(self) -> "LessonPlan":
        words = sum(len(s.narration.split()) for s in self.scenes)
        est = words / SPEECH_WPS + TAIL * len(self.scenes)
        if not (TOTAL_MIN <= words <= TOTAL_MAX) or not (EST_SEC_MIN <= est <= EST_SEC_MAX):
            raise ValueError(f"total {words} words (~{est:.0f}s) out of range: need {TOTAL_MIN}-{TOTAL_MAX} words")
        return self
