# orchestrator/cache.py — Tier 1: validated English plans at cache/plans/{slug}.json
import re
from pathlib import Path

from pydantic import ValidationError

from orchestrator.schema import LessonPlan

PLAN_DIR = Path(__file__).resolve().parent.parent / "cache" / "plans"


def topic_slug(topic: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", topic.strip().lower()).strip("-") or "untitled"


def load_plan(topic: str, plan_dir: Path | None = None) -> LessonPlan | None:
    path = (plan_dir or PLAN_DIR) / f"{topic_slug(topic)}.json"
    try:
        return LessonPlan.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None


def save_plan(topic: str, plan: LessonPlan, plan_dir: Path | None = None) -> Path:
    plan_dir = plan_dir or PLAN_DIR
    plan_dir.mkdir(parents=True, exist_ok=True)
    path = plan_dir / f"{topic_slug(topic)}.json"
    path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    return path
