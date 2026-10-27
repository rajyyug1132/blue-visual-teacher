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
    def install(*outputs, has_formula=True, patches=()):
        client = FakeClient(*outputs, has_formula=has_formula, patches=patches)
        monkeypatch.setattr(planner, "_client", client)
        monkeypatch.setattr(planner, "ESCALATION_MODEL", "")
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
    assert any(p.startswith("Remove '=' from scene 3 label") for p in problems)


def test_monsoon_with_invented_formula_never_reaches_the_plan(fake):
    bad = json.dumps(monsoon(scene3_labels=["Moist sea winds", "V = Rain / (A × T)"]))
    client = fake(bad, bad, DESCRIPTIVE_JSON, has_formula=False)
    plan, tel = planner.plan_lesson("Monsoon")
    assert "Remove '=' from scene 3 label" in client.calls[1]["messages"][-1]["content"]
    assert tel["stage"] == "qualitative"
    assert not any("=" in t for s in plan.scenes for t in s.visual.params.labels + s.visual.params.steps)


# --- 2. spoken quantity in a descriptive topic -----------------------------------------------------------------

def test_fifty_five_degrees_celsius_is_rejected_in_a_descriptive_topic():
    plan = monsoon(scene4_narration="In Mumbai the monsoon air is hot and humid, around fifty-five degrees "
                                    "Celsius, as winds blow in from the southwest.")
    problems = audit_numbers(plan, "none")
    assert any(p.startswith("Remove the numbers (55) from scene 4 narration") for p in problems)
    assert any(p.startswith("Remove the unit 'degrees' from scene 4 narration") for p in problems)


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


# --- second round: fixes from the 20-topic stress run -----------------------------------------------------------

def test_retry_messages_never_offer_words_to_copy():
    plan = monsoon(scene4_narration="In Mumbai the monsoon brings two hundred centimetres of rain over four "
                                    "months, around fifty-five degrees Celsius, as winds blow in.")
    plan["scenes"][2]["visual"]["params"]["labels"] = ["Rain = Wind × Moisture"]
    problems = audit_numbers(plan, "none")
    assert problems and all(p.startswith("Remove ") and "keep the" in p for p in problems)
    assert not any(w in " ".join(problems) for w in ("heavy rain", "several months", "much larger", "e.g."))


def test_years_are_allowed_in_descriptive_topics():
    plan = json.loads(DESCRIPTIVE_JSON)
    plan["scenes"][0]["narration"] = ("Why did India finally win independence in nineteen forty-seven, after the "
                                      "Salt March of nineteen thirty and decades of protest?")
    plan["scenes"][0]["visual"]["params"]["labels"] = ["Indian Independence", "1930-1947", "Freedom Struggle"]
    plan["scenes"][1]["narration"] = ("In the nineteen sixties new seeds and canals changed farming across Punjab, "
                                      "and harvests grew year after year.")
    plan["scenes"][2]["narration"] = ("Ashoka ruled from 268 BCE, and Chandragupta Maurya from 321 BCE, long before "
                                      "the Gupta age of AD 320.")
    plan["scenes"][2]["visual"]["params"]["labels"] = ["321-185 BCE", "563 BC", "78 CE"]
    assert audit_numbers(plan, "none") == []
    assert spoken_numbers("the nineteen sixties") == [1960] and spoken_numbers("nineteen sixty") == [1960]


@pytest.mark.parametrize("text, bad", [
    ("Over 1,500 soldiers marched to Delhi with the emperor.", "1500"),
    ("The army had 321 soldiers under a strong commander.", "321"),  # unmarked count, not a date
    ("Nearly two thousand villages joined the movement within weeks.", "2000"),  # a count, not a year
])
def test_non_year_numbers_are_still_banned(text, bad):
    plan = json.loads(DESCRIPTIVE_JSON)
    plan["scenes"][0]["narration"] = text
    assert any(f"({bad})" in p for p in audit_numbers(plan, "none"))


@pytest.mark.parametrize("expr, value", [
    ("10² + 6²", 136), ("c² = 6² + 8²", 100), ("100 = 36 + 64", 100), ("√(6² + 8²)", 10), ("√100", 10),
])
def test_safe_eval_powers_roots_and_equations(expr, value):
    from orchestrator.mathcheck import safe_eval
    assert safe_eval(expr) == pytest.approx(value)


@pytest.mark.parametrize("expr", ["V / R where V = 230", "x = 230", "100 = 36 + 65"])
def test_safe_eval_rejects_bad_equations(expr):
    from orchestrator.mathcheck import MathCheckError, safe_eval
    with pytest.raises(MathCheckError):
        safe_eval(expr)


def test_answer_that_cannot_fit_moves_to_the_next_rung_without_filler(fake):
    unfit = json.dumps(compound_interest(  # one 31-word sentence with no clause break to trim at
        "Save one hundred rupees in a small bank near your home at five percent yearly interest for ten long years "
        "without taking out any money at all during that whole time"))
    client = fake(unfit, unfit, DESCRIPTIVE_JSON)
    plan, tel = planner.plan_lesson("Compound Interest")
    assert tel["errors"][1].startswith("retry:") and "within 32 words" in tel["errors"][1]
    assert tel["stage"] == "qualitative" and len(client.calls) == 3
    assert not any("work through the steps shown on screen" in s.narration for s in plan.scenes)


def test_check_copied_from_another_topic_is_rejected():
    from orchestrator.mathcheck import MathCheckError
    plan = json.loads(OHM_JSON)  # Ohm's check "230 / 46", but scene 4 now teaches titration
    scene = plan["scenes"][3]
    scene["narration"] = ("In a titration we add base to the acid drop by drop until the indicator changes "
                          "colour at the end point.")
    scene["visual"]["params"] = {"labels": ["Acid in flask", "Base in burette", "Indicator turns pink"],
                                 "steps": ["Add base slowly", "Stop at colour change"]}
    with pytest.raises(MathCheckError, match="uses 230, 46, which this scene never shows"):
        verify_plan(plan)


# --- short scene 1 is extended from the title, not retried --------------------------------------------------------

def test_short_hook_is_extended_from_the_title_without_a_retry(fake):
    plan = json.loads(DESCRIPTIVE_JSON)
    plan["scenes"][0]["narration"] = "How does a clerk find one booking among sorted records?"  # 10 words
    client = fake(json.dumps(plan), has_formula=False)
    result, tel = planner.plan_lesson("Binary Search")
    assert len(client.calls) == 1 and tel["stage"] == "plan" and tel["hook_extended"] is True
    assert result.scenes[0].narration == ("How does a clerk find one booking among sorted records? "
                                          "Today we explore Binary Search, Halving the Search Space.")


def test_very_short_hook_gets_a_second_filler_sentence(fake):
    plan = json.loads(DESCRIPTIVE_JSON)
    plan["title"] = "Binary Search"
    plan["scenes"][0]["narration"] = "Ever searched a phone book?"  # 5 words
    fake(json.dumps(plan), has_formula=False)
    result, tel = planner.plan_lesson("Binary Search")
    narration = result.scenes[0].narration
    assert tel["hook_extended"] is True and len(narration.split()) >= 14
    assert narration == "Ever searched a phone book? Today we explore Binary Search. Let's find out how it works."


def test_hook_extension_cannot_smuggle_numbers_from_the_title(fake):
    plan = json.loads(DESCRIPTIVE_JSON)
    plan["title"] = "GST: The 18% Tax on Goods"
    plan["scenes"][0]["narration"] = "Why does your grocery bill show an extra tax line?"  # 10 words
    client = fake(json.dumps(plan), has_formula=False)  # retry and later rungs fail -> template
    _, tel = planner.plan_lesson("GST")
    assert "Remove the numbers (18) from scene 1 narration" in client.calls[1]["messages"][-1]["content"]


# --- patch rung: rewrite just the flagged strings instead of re-planning -----------------------------------------

def test_descriptive_numbers_are_patched_in_place_without_a_replan(fake):
    bad = json.dumps(monsoon(scene4_narration="Kerala gets about two thousand millimetres of rain from June to "
                                              "September, which fills its rivers and wells."))
    client = fake(bad, has_formula=False,
                  patches=["Kerala gets very heavy rain through the monsoon months, which fills its rivers and wells."])
    plan, tel = planner.plan_lesson("Monsoon")
    assert tel["stage"] == "plan+patch" and len(client.calls) == 1 and len(client.patch_calls) == 1
    prompt = client.patch_calls[0]["messages"][0]["content"]
    assert "contains no numbers or amounts" in prompt and "no units of measurement" in prompt
    assert "heavy rain" not in prompt.split("\n\n")[0]  # the rule never offers words to copy
    assert plan.scenes[3].narration.startswith("Kerala gets very heavy rain")


def test_a_patch_that_still_breaks_the_rule_falls_through_to_the_retry(fake):
    bad = json.dumps(monsoon(scene4_narration="Kerala gets about two thousand millimetres of rain from June to "
                                              "September, which fills its rivers and wells."))
    client = fake(bad, DESCRIPTIVE_JSON, has_formula=False,
                  patches=["Kerala gets nearly two thousand millimetres of rain, which fills its rivers and wells."])
    _, tel = planner.plan_lesson("Monsoon")
    assert tel["stage"] == "retry" and len(client.patch_calls) == 1


def test_keyword_prior_marks_formula_topics_checked_without_a_classify_call(fake):
    client = fake(OHM_JSON, has_formula=False)  # the classifier would say no; the keyword decides first
    _, tel = planner.plan_lesson("Pythagoras Theorem")
    assert tel["policy"] == "checked" and client.classify_calls == []
