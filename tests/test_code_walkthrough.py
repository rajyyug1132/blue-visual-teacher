# CC-2: the code_walkthrough scene type. The planner writes code and a variable trace as DATA;
# nothing here is ever executed, so these tests pin the shape, the bounds and the fact that the
# numeric audit ignores code (source lines legitimately contain digits).
import copy
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.numeric_guard import audit_numbers
from orchestrator.schema import CODE_LINE_CHARS, LessonPlan, VisualSpec

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "golden_ohms_law.json"

CODE = ["for i in range(3):", "    print(i)"]
TRACE = [
    {"line": 1, "vars": [{"name": "i", "value": "0"}]},
    {"line": 2, "vars": [{"name": "i", "value": "0"}]},
    {"line": 1, "vars": [{"name": "i", "value": "1"}]},
]


def walkthrough(**over):
    params = {"labels": ["Python for loop"], "steps": ["i takes each value in turn"],
              "code": list(CODE), "trace": copy.deepcopy(TRACE)}
    params.update(over)
    return {"type": "code_walkthrough", "params": params}


def test_valid_code_walkthrough_scene():
    v = VisualSpec.model_validate(walkthrough())
    assert [s.line for s in v.params.trace] == [1, 2, 1]
    assert v.params.trace[2].vars[0].value == "1"


def test_trace_line_past_end_of_code_is_rejected():
    bad = walkthrough(trace=[{"line": 7, "vars": [{"name": "i", "value": "0"}]}])
    with pytest.raises(ValidationError, match="past the end of code"):
        VisualSpec.model_validate(bad)


def test_code_walkthrough_needs_code_and_trace():
    with pytest.raises(ValidationError, match="needs visual.params.code"):
        VisualSpec.model_validate(walkthrough(code=[]))
    with pytest.raises(ValidationError, match="needs visual.params.trace"):
        VisualSpec.model_validate(walkthrough(trace=[]))


def test_other_visual_types_may_not_carry_code_or_trace():
    with pytest.raises(ValidationError, match="code_walkthrough only"):
        VisualSpec.model_validate({"type": "flow", "params": {
            "labels": ["a"], "steps": ["b"], "code": list(CODE), "trace": copy.deepcopy(TRACE)}})


def test_code_line_length_is_capped():
    with pytest.raises(ValidationError, match="max 80"):
        VisualSpec.model_validate(walkthrough(code=["x" * (CODE_LINE_CHARS + 1), "pass"]))


def test_golden_fixture_still_validates():
    plan = LessonPlan.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert [s.visual.type for s in plan.scenes] == ["title", "compare", "equation", "flow", "bullets"]
    assert all(s.visual.params.code == [] and s.visual.params.trace == [] for s in plan.scenes)


def test_lesson_validates_with_a_code_walkthrough_scene():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["scenes"][3]["visual"] = walkthrough()
    data["scenes"][3].pop("check", None)
    plan = LessonPlan.model_validate(data)
    assert plan.scenes[3].visual.type == "code_walkthrough"


def test_code_walkthrough_reaches_the_ollama_grammar():
    schema = json.dumps(LessonPlan.model_json_schema())
    assert "code_walkthrough" in schema
    assert "CodeStep" in schema and "VarState" in schema


def test_numeric_audit_ignores_digits_inside_code():
    # Policy "none" forbids quantities, but source lines are not prose: range(3) must not be flagged.
    data = {"scenes": [{"id": 1, "narration": "The loop repeats the body once for every item in the list.",
                        "visual": walkthrough()}]}
    assert audit_numbers(data, "none") == []


def test_numeric_audit_still_catches_digits_in_labels():
    data = {"scenes": [{"id": 1, "narration": "The loop repeats the body once for every item in the list.",
                        "visual": walkthrough(labels=["Runs 400 times"])}]}
    assert audit_numbers(data, "none"), "a number in a label must still be reported"
