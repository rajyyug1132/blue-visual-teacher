# orchestrator/cache.py — Tier 1: validated English plans at cache/plans/{slug}.json
import re
from pathlib import Path

from pydantic import ValidationError

from orchestrator.schema import LessonPlan

PLAN_DIR = Path(__file__).resolve().parent.parent / "cache" / "plans"
DEFAULT_LEVEL, DEFAULT_TARGET_SEC = "beginner", 60


def topic_slug(topic: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", topic.strip().lower()).strip("-") or "untitled"


def plan_stem(topic: str, level: str = DEFAULT_LEVEL, target_sec: int = DEFAULT_TARGET_SEC) -> str:
    """Plan files are keyed by level and length so "beginner 30 s" never returns the "intermediate 90 s" plan.

    The default pair keeps the historical {slug} name, so the plans cached before CC-2 still hit.
    """
    slug = topic_slug(topic)
    if (level, target_sec) == (DEFAULT_LEVEL, DEFAULT_TARGET_SEC):
        return slug
    return f"{slug}__{level}__{int(target_sec)}s"


def load_plan(topic: str, plan_dir: Path | None = None, level: str = DEFAULT_LEVEL,
              target_sec: int = DEFAULT_TARGET_SEC) -> LessonPlan | None:
    path = (plan_dir or PLAN_DIR) / f"{plan_stem(topic, level, target_sec)}.json"
    try:
        return LessonPlan.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None


def save_plan(topic: str, plan: LessonPlan, plan_dir: Path | None = None, level: str | None = None,
              target_sec: int | None = None) -> Path:
    plan_dir = plan_dir or PLAN_DIR
    plan_dir.mkdir(parents=True, exist_ok=True)
    path = plan_dir / f"{plan_stem(topic, level or plan.level, target_sec or plan.target_sec)}.json"
    path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    return path
