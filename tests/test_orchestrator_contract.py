import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.schema import LessonPlan

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "golden_ohms_law.json"


def test_golden_fixture_validates_with_expected_word_counts():
    plan = LessonPlan.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert [len(s.narration.split()) for s in plan.scenes] == [22, 27, 24, 28, 21]
    assert [s.visual.type for s in plan.scenes] == ["title", "compare", "equation", "flow", "bullets"]
