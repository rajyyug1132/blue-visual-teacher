import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from orchestrator import planner
from orchestrator.mathcheck import replace_result, verify_plan
from orchestrator.numeric_guard import audit_numbers, spoken_numbers
from orchestrator.prompts import FEW_SHOT_MESSAGES
from orchestrator.schema import WORDS_MAX, LessonPlan
from test_orchestrator import FakeClient, tmp_cache  # noqa: F401  (autouse fixture: isolated plan cache)

OHM_JSON = FEW_SHOT_MESSAGES[1]["content"]  # policy "checked"
DESCRIPTIVE_JSON = FEW_SHOT_MESSAGES[3]["content"]  # policy "none"


@pytest.fixture
def fake(monkeypatch):
    def install(*outputs, has_formula=True):
        client = FakeClient(*outputs, has_formula=has_formula)
        monkeypatch.setattr(planner, "_client", client)
        return client
    return install


def monsoon(scene3_labels=None, scene4_narration=None) -> dict:
    plan = json.loads(DESCRIPTIVE_JSON)
    plan["title"] = "Monsoon: Rain Across India"
    if scene3_labels:
        plan["scenes"][2]["visual"]["params"]["labels"] = scene3_labels
    if scene4_narration:
        plan["scenes"][3]["narration"] = scene4_narration
    return plan


# --- 1. invented formula in a descriptive topic ----------------------------------------------------------------

def test_monsoon_with_invented_formula_is_rejected():
    plan = monsoon(scene3_labels=["Moist sea winds", "V = Rain / (A × T)", "Rain over the Ghats"])
    problems = audit_numbers(plan, "none")
    assert any("contains '='" in p and "V = Rain / (A × T)" in p for p in problems)


def test_monsoon_with_invented_formula_never_reaches_the_plan(fake):
    bad = json.dumps(monsoon(scene3_labels=["Moist sea winds", "V = Rain / (A × T)"]))
    client = fake(bad, bad, DESCRIPTIVE_JSON, has_formula=False)
    plan, tel = planner.plan_lesson("Monsoon")
    assert "contains '='" in client.calls[1]["messages"][-1]["content"]
    assert tel["stage"] == "qualitative"
    assert not any("=" in t for s in plan.scenes for t in s.visual.params.labels + s.visual.params.steps)


# --- 2. spoken quantity in a descriptive topic -----------------------------------------------------------------

def test_fifty_five_degrees_celsius_is_rejected_in_a_descriptive_topic():
    plan = monsoon(scene4_narration="In Mumbai the monsoon air is hot and humid, around fifty-five degrees "
                                    "Celsius, as winds blow in from the southwest.")
    problems = audit_numbers(plan, "none")
    assert any("has quantities 55" in p for p in problems)
    assert any("unit 'degrees'" in p for p in problems)


def test_spoken_numbers_parser():
    assert spoken_numbers("around fifty-five degrees Celsius") == [55]
    assert spoken_numbers("one hundred twenty-eight thousand rupees") == [128000]
    assert spoken_numbers("one lakh and fifty thousand") == [150000]
    assert spoken_numbers("three point one four") == [3.14]
    assert spoken_numbers("the point is, a hundred people came") == []


# --- 3. the worked example must say its answer ------------------------------------------------------------------

def compound_interest(narration: str) -> dict:
    plan = json.loads(OHM_JSON)
    scene = plan["scenes"][3]
    scene["narration"] = narration
    scene["check"] = {"expr": "100 * (1 + 0.05) ** 10", "result": "162.89 rupees"}
    scene["visual"]["params"] = {"labels": ["P = 100", "r = 5%", "t = 10"],
                                 "steps": ["100 × (1 + 0.05)^10 = 162.89"]}
    return plan


def test_compound_interest_without_the_result_is_repaired_to_say_it(fake):
    silent = json.dumps(compound_interest(
        "Save one hundred rupees at five percent interest for ten years with yearly compounding."))
    client = fake(silent, silent)
    plan, tel = planner.plan_lesson("Compound Interest")
    assert "must say the final answer, one hundred sixty-two point eight nine rupees" in \
        client.calls[1]["messages"][-1]["content"]  # first: one retry asking for it
    assert tel["stage"] == "retry" and tel["answer_repaired"] is True  # then: deterministic repair
    assert plan.scenes[3].narration == ("Save one hundred rupees at five percent interest for ten years with yearly "
                                        "compounding. So the answer is one hundred sixty-two point eight nine rupees.")
    assert 162.89 in spoken_numbers(plan.scenes[3].narration)


def test_answer_repair_trims_an_earlier_clause_to_fit(fake):
    long_silent = json.dumps(compound_interest(
        "Save one hundred rupees in a bank at five percent interest for ten years, and the bank adds interest "
        "on your interest every single year, which slowly snowballs."))  # 30 words
    fake(long_silent, long_silent)
    plan, tel = planner.plan_lesson("Compound Interest")
    narration = plan.scenes[3].narration
    assert tel["answer_repaired"] is True and len(narration.split()) <= WORDS_MAX
    assert narration.endswith("So the answer is one hundred sixty-two point eight nine rupees.")


# --- 4. compatibility forms are caught after NFKC ---------------------------------------------------------------

@pytest.mark.parametrize("narration", [
    "Leaves breathe in CO₂ from the air and use sunlight to turn it into sugar for the tree.",
    "Heavy rain falls over every km² of the Western Ghats during the wettest weeks of the season.",
])
def test_subscripts_and_superscripts_are_rejected_after_nfkc(narration):
    plan = json.loads(DESCRIPTIVE_JSON)
    plan["scenes"][0]["narration"] = narration
    with pytest.raises(ValidationError, match="spoken words only"):
        LessonPlan.model_validate(plan)


def test_planner_speaks_co2_as_carbon_dioxide(fake):
    plan = json.loads(DESCRIPTIVE_JSON)
    plan["scenes"][0]["narration"] = "Leaves breathe in CO₂ from the air and use sunlight to turn it into sugar."
    fake(json.dumps(plan), has_formula=False)
    result, tel = planner.plan_lesson("Photosynthesis")
    assert "carbon dioxide" in result.scenes[0].narration and tel["stage"] == "plan"


# --- 5. position-based replacement ------------------------------------------------------------------------------

def test_only_the_result_span_changes_not_the_five_percent_input():
    assert replace_result("At a 5% discount on 120 rupees, the saving is 5 rupees.", wrong=5, right="6") == \
        "At a 5% discount on 120 rupees, the saving is 6 rupees."
    assert replace_result("120 × 5% = 5", wrong=5, right="6") == "120 × 5% = 6"
    assert replace_result("five percent off gives five rupees", wrong=5, right="6", spoken=True) == \
        "five percent off gives 6 rupees"


def test_verify_plan_fixes_result_but_keeps_the_rate():
    plan = json.loads(OHM_JSON)
    scene = plan["scenes"][3]
    scene["narration"] = "A shop gives a 5% discount on 120 rupees, so the saving is 5 rupees."
    scene["check"] = {"expr": "120 * 5 / 100", "result": "5"}
    scene["visual"]["params"] = {"labels": ["Price: 120", "Discount: 5%"], "steps": ["120 × 5% = 5"]}
    report = verify_plan(plan)
    assert report["status"] == "fixed" and report["computed"] == 6
    assert scene["narration"] == "A shop gives a 5% discount on 120 rupees, so the saving is 6 rupees."
    assert scene["visual"]["params"] == {"labels": ["Price: 120", "Discount: 5%"], "steps": ["120 × 5% = 6"]}
    assert scene["check"]["result"] == "6"


# --- 6. small structural counts are fine ------------------------------------------------------------------------

@pytest.mark.parametrize("policy", ["none", "checked"])
def test_three_takeaways_is_allowed(policy):
    plan = json.loads(DESCRIPTIVE_JSON)
    plan["scenes"][4]["narration"] = ("To recap, here are three takeaways: sorted data first, check the middle, "
                                      "and halve the range each time.")
    plan["scenes"][4]["visual"]["params"]["steps"] = ["Step 1: Sort", "2. Check the middle", "Three takeaways"]
    assert audit_numbers(plan, policy) == []
