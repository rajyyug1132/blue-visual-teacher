# orchestrator/schema.py
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
