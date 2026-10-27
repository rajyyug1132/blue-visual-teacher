import json
import sys
import time
from pathlib import Path

import ollama
import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import cache, planner, schema
from orchestrator.fallbacks import build_safe_fallback_lesson
from orchestrator.prompts import FEW_SHOT_MESSAGES
from orchestrator.schema import LessonPlan

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_JSON = (ROOT / "fixtures" / "golden_ohms_law.json").read_text(encoding="utf-8")
GOOD_JSON = FEW_SHOT_MESSAGES[1]["content"]  # Ohm's Law as a model reply: the fixture plus a worked-example check

TOPICS = [
    "Photosynthesis", "Newton's Third Law", "Binary Search", "Supply and Demand", "DNA Replication",
    "Pythagoras Theorem", "Water Cycle", "Compound Interest", "Acid-Base Titration", "TCP Three-Way Handshake",
    "Indian Independence Movement", "Monsoon", "GST", "Mughal Empire", "Democracy",
    "", "x",
    "Electromagnetic Induction In Transformers",  # 41 chars
    "Supercalifragilisticexpialidociousnesses",  # 40 chars, one word
    "the quick brown fox jumps over the lazy dog and keeps on running",
    "TCP/IP", "Web 3.0", "E=mc2", "50% Rule", "V = I × R", "Ω and Resistance",  # symbols must not reach narration
]


def words(plan: LessonPlan) -> list[int]:
    return [len(s.narration.split()) for s in plan.scenes]


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "PLAN_DIR", tmp_path / "plans")


class FakeClient:
    """Stands in for ollama.Client; each queued item is returned (str content) or raised (exception)."""

    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return ollama.ChatResponse(
            model="fake", message=ollama.Message(role="assistant", content=out),
            prompt_eval_count=10, eval_count=20, eval_duration=1_000_000, load_duration=0,
        )


@pytest.fixture
def fake(monkeypatch):
    def install(*outputs):
        client = FakeClient(*outputs)
        monkeypatch.setattr(planner, "_client", client)
        return client
    return install


def test_fixture_validates_and_total_words_in_target():
    plan = LessonPlan.model_validate_json(GOLDEN_JSON)
    assert len(plan.scenes) == 5
    assert 100 <= sum(words(plan)) <= 140


def test_few_shot_examples_validate_and_total_words_in_target():
    for msg in FEW_SHOT_MESSAGES[1::2]:
        assert 100 <= sum(words(LessonPlan.model_validate_json(msg["content"]))) <= 140


@pytest.mark.parametrize("topic", TOPICS)
def test_fallback_is_valid_for_any_topic(topic):
    plan = build_safe_fallback_lesson(topic)
    assert all(schema.WORDS_MIN <= w <= schema.WORDS_MAX for w in words(plan))
    assert not any(schema.NOT_SPOKEN.search(s.narration) for s in plan.scenes)
    assert schema.TOTAL_MIN <= sum(words(plan)) <= schema.TOTAL_MAX
    LessonPlan.model_validate_json(plan.model_dump_json())  # survives a JSON round trip


def test_fallback_keeps_acronyms():
    assert build_safe_fallback_lesson("DNA replication").scenes[0].visual.params.labels[0] == "DNA Replication"


def test_good_response_returns_plan_and_caches(fake):
    client = fake(GOOD_JSON)
    plan, tel = planner.plan_lesson("Ohm's Law")
    assert tel["fallback_used"] is False and tel["attempt"] == 1 and tel["total_words"] == 123
    call = client.calls[0]
    assert call["keep_alive"] == -1 and call["model"] == planner.MODEL_NAME
    assert "think" not in call  # qwen2.5 is not a thinking model
    assert call["format"] == LessonPlan.model_json_schema()
    assert cache.load_plan("ohm's law  ") == plan


def test_bad_json_then_retry_then_fallback(fake):
    client = fake("not json at all", '{"title": "x"}')
    plan, tel = planner.plan_lesson("Ohm's Law")
    assert tel["fallback_used"] is True and tel["attempt"] == 3
    assert len(client.calls) == 2
    # The retry carries the bad output and the validation error back to the model.
    retry_msgs = client.calls[1]["messages"]
    assert retry_msgs[-2] == {"role": "assistant", "content": "not json at all"}
    assert "Validation failed" in retry_msgs[-1]["content"]
    assert cache.load_plan("Ohm's Law") is None  # fallbacks are never cached


def test_bad_json_then_good_retry(fake):
    fake("{", GOOD_JSON)
    _, tel = planner.plan_lesson("Ohm's Law")
    assert tel["fallback_used"] is False and tel["attempt"] == 2


def test_daemon_down_falls_back_without_crashing(fake):
    client = fake(ConnectionError("refused"), ConnectionError("refused"))
    plan, tel = planner.plan_lesson("Monsoon")
    assert tel["fallback_used"] is True and len(tel["errors"]) == 2
    assert all(m["role"] != "assistant" or m in FEW_SHOT_MESSAGES for m in client.calls[1]["messages"])


@pytest.mark.parametrize("model", ["qwen3:4b", "gemma4:e4b"])
def test_thinking_models_get_think_false(fake, model):
    client = fake(GOOD_JSON)
    planner.plan_lesson("Ohm's Law", model=model)
    assert client.calls[0]["think"] is False


def test_model_rejecting_think_is_retried_without_flag(fake):
    client = fake(ollama.ResponseError('"gemma2" does not support thinking'), GOOD_JSON)
    _, tel = planner.plan_lesson("Ohm's Law", model="gemma2:2b")
    assert tel["fallback_used"] is False and tel["attempt"] == 1
    assert client.calls[0]["think"] is False and "think" not in client.calls[1]


def test_default_model_is_qwen_7b(monkeypatch):
    import importlib
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    assert importlib.reload(planner).MODEL_NAME == "qwen2.5:7b"


def test_model_name_comes_from_env(monkeypatch):
    import importlib
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    try:
        assert importlib.reload(planner).MODEL_NAME == "llama3.2:3b"
    finally:
        monkeypatch.delenv("OLLAMA_MODEL")
        importlib.reload(planner)


def test_lesson_total_below_range_retries_with_total_feedback(fake):
    short = json.loads(GOOD_JSON)
    short["scenes"] = short["scenes"][:4]
    for s in short["scenes"]:
        s["narration"] = "Voltage pushes current through a wire while resistance slows it down in every circuit."  # 14
    payload = json.dumps(short)  # every scene valid, lesson total 56 words < 85
    client = fake(payload, payload)
    _, tel = planner.plan_lesson("Ohm's Law")
    feedback = client.calls[1]["messages"][-1]["content"]
    assert "total 56 words" in feedback and f"{schema.TOTAL_MIN}-{schema.TOTAL_MAX} words" in feedback
    assert tel["fallback_used"] is True


@pytest.mark.parametrize("narration", [
    "Let's test a 230-Volt Indian wall socket connected to an iron box with forty-six ohms resistance today.",
    "Georg Ohm showed that V = I × R holds for many metals when the temperature stays the same.",
    "Interest grows at ten % every year, so the money in your account keeps climbing each year.",
])
def test_narration_must_be_spoken_words_only(narration):
    plan = json.loads(GOLDEN_JSON)
    plan["scenes"][0]["narration"] = narration
    with pytest.raises(ValidationError, match="spoken words only"):
        LessonPlan.model_validate(plan)


def test_cache_hit_under_5ms(fake):
    cache.save_plan("Ohm's Law", LessonPlan.model_validate_json(GOLDEN_JSON))
    fake()  # any LLM call would pop from an empty queue and fail
    best_ms = float("inf")
    for _ in range(3):  # best of 3: one Windows scheduler stall should not fail the suite
        t0 = time.perf_counter()
        plan, tel = planner.plan_lesson("  OHM'S LAW ")
        best_ms = min(best_ms, (time.perf_counter() - t0) * 1000)
    assert tel["cache_hit"] is True and len(plan.scenes) == 5
    assert best_ms < 5, f"cache hit took {best_ms:.2f} ms"


def test_duration_gate():
    from orchestrator.pipeline import DurationGateError, duration_gate

    assert duration_gate([{"end_sec": 12.0}, {"end_sec": 54.79}]) == 54.79
    for total in (29.99, 90.01):
        with pytest.raises(DurationGateError, match="outside 30-90s"):
            duration_gate([{"end_sec": total}])
    with pytest.raises(DurationGateError):
        duration_gate([])


def test_corrupt_cache_file_is_ignored(fake):
    cache.PLAN_DIR.mkdir(parents=True)
    (cache.PLAN_DIR / "monsoon.json").write_text("{broken", encoding="utf-8")
    assert cache.load_plan("Monsoon") is None


def test_stub_pipeline_timing_follows_word_rate(tmp_path):
    import wave

    import run_pipeline
    from orchestrator.pipeline import duration_gate

    plan = LessonPlan.model_validate_json(GOLDEN_JSON)
    wav = tmp_path / "a.wav"
    manifest = run_pipeline.StubTTSEngine().synthesize_all_scenes(plan.scenes, "en", str(wav))
    # words [22, 27, 24, 29, 21] at 2.3 words/s + 0.35 s tail
    assert [m["duration_sec"] for m in manifest] == [9.915, 12.089, 10.785, 12.959, 9.48]
    assert duration_gate(manifest) == pytest.approx(55.23, abs=0.01)
    with wave.open(str(wav)) as w:
        assert w.getnframes() / w.getframerate() == pytest.approx(55.23, abs=0.01)


def test_retry_names_the_overlong_scene(fake):
    plan = json.loads(GOOD_JSON)
    plan["scenes"][2]["narration"] = " ".join(["word"] * 45)
    client = fake(json.dumps(plan), GOOD_JSON)
    _, tel = planner.plan_lesson("Ohm's Law")
    feedback = client.calls[1]["messages"][-1]["content"]
    assert "Scene 3 narration" in feedback and "18-28 spoken words" in feedback
    assert tel["attempt"] == 2 and tel["fallback_used"] is False


GRAMMAR_CUT = ("The formula for Compound Interest is A equals P times (one plus r over n) to the power of nt, where A "
               "is the final amount, P is the principal, r is the annual interest rate, n is the number of times "
               "interest is compounded per year, and t is a")


def test_overlong_single_sentence_is_cut_at_main_clause():
    assert planner._shorten_narration(GRAMMAR_CUT) == (
        "The formula for Compound Interest is A equals P times (one plus r over n) to the power of nt.")


def test_overlong_narration_keeps_whole_sentences():
    first = "Compound interest means the bank pays interest on your savings and also on the interest already earned."
    text = first + " " + " ".join(["more"] * 40) + "."
    assert planner._shorten_narration(text) == first


def test_too_short_kept_sentences_are_not_used():
    text = "Interest grows on interest. " + " ".join(["more"] * 40) + "."
    assert planner._shorten_narration(text) is None  # four words would fail the per-scene minimum


def test_repaired_plan_is_used_without_retry(fake):
    plan = json.loads(GOOD_JSON)
    plan["scenes"][2]["narration"] = GRAMMAR_CUT
    client = fake(json.dumps(plan))
    result, tel = planner.plan_lesson("Compound Interest")
    assert len(client.calls) == 1 and tel["repaired"] is True and tel["fallback_used"] is False
    assert result.scenes[2].narration.endswith("power of nt.")


def test_unrepairable_narration_still_retries(fake):
    plan = json.loads(GOOD_JSON)
    plan["scenes"][2]["narration"] = " ".join(["word"] * 45)  # no sentence or clause break to cut at
    client = fake(json.dumps(plan), json.dumps(plan))
    _, tel = planner.plan_lesson("Ohm's Law")
    assert len(client.calls) == 2 and tel["fallback_used"] is True


@pytest.mark.parametrize("text, spoken", [
    ("Dividing 230 Volts by 46 Ω gives 5 A.", "Dividing two hundred thirty Volts by forty-six ohms gives five A."),
    ("Plants turn 6CO2 and 6H2O into sugar.", "Plants turn six CO two and six H two O into sugar."),
    ("Rs. 10,000 at 5% grows to Rs. 12,762.82.",
     "ten thousand rupees at five percent grows to twelve thousand seven hundred sixty-two point eight two rupees."),
    ("India became free in 1947, and in 2005 had 1,00,000 users.",
     "India became free in nineteen forty-seven, and in two thousand five had one hundred thousand users."),
    ("The 21st, 3rd and 12th runs.", "The twenty-first, third and twelfth runs."),
    ("Find 72 in 10, 30, 50, 72, 90.", "Find seventy-two in ten, thirty, fifty, seventy-two, ninety."),
    ("So I = V/R here.", "So I equals V over R here."),
    ("Save $100 to get $162.89.", "Save one hundred dollars to get one hundred sixty-two point eight nine dollars."),
])
def test_to_spoken(text, spoken):
    from orchestrator.spoken import to_spoken

    assert to_spoken(text) == spoken
    assert not schema.NOT_SPOKEN.search(spoken)


def test_digits_in_narration_are_repaired_without_retry(fake):
    plan = json.loads(GOOD_JSON)
    plan["scenes"][3]["narration"] = ("Let's test a 230-Volt Indian wall socket powering an iron box with 46 Ohms "
                                      "resistance. Dividing 230 by 46 gives 5 Amperes.")
    client = fake(json.dumps(plan))
    result, tel = planner.plan_lesson("Ohm's Law")
    assert len(client.calls) == 1 and tel["repaired"] is True and tel["fallback_used"] is False
    assert result.scenes[3].narration == ("Let's test a two hundred thirty Volt Indian wall socket powering an iron "
                                          "box with forty-six Ohms resistance. Dividing two hundred thirty by "
                                          "forty-six gives five Amperes.")  # 26 words after spelling out, no trim


def test_digits_then_overlong_main_clause_is_repaired(fake):
    plan = json.loads(GOOD_JSON)
    plan["scenes"][2]["narration"] = GRAMMAR_CUT.replace("(one plus", "(1 plus")
    fake(json.dumps(plan))
    result, tel = planner.plan_lesson("Compound Interest")
    assert tel["repaired"] is True
    assert result.scenes[2].narration == (
        "The formula for Compound Interest is A equals P times (one plus r over n) to the power of nt.")


def test_device_env(monkeypatch):
    from orchestrator.device import get_device

    monkeypatch.delenv("DEVICE", raising=False)
    assert get_device() == "cpu"  # GPU is reserved for the qwen2.5:7b planner
    monkeypatch.setenv("DEVICE", "CPU")
    assert get_device() == "cpu"
    monkeypatch.setenv("DEVICE", "cuda")
    assert get_device() in ("cuda", "cpu")  # cpu when torch/CUDA is missing
    monkeypatch.setenv("DEVICE", "tpu")
    with pytest.raises(ValueError):
        get_device()


# --- math guard -------------------------------------------------------------------------------------------------

def test_safe_eval_compound_interest():
    from orchestrator.mathcheck import safe_eval

    assert round(safe_eval("100*(1+0.05)**10"), 2) == 162.89
    assert safe_eval("230 / 46") == 5
    assert safe_eval("10,000 × 1.05^2") == pytest.approx(11025)


@pytest.mark.parametrize("expr", [
    '__import__("os").system("x")', "x + 1", "open", "(1).real", "[1, 2]", "1 if 1 else 2",
    "9 ** 999", "2 ** 10 ** 10", "1e6 ** 100", "1 / 0", "", "lambda: 1",
])
def test_safe_eval_rejects_anything_but_arithmetic(expr):
    from orchestrator.mathcheck import MathCheckError, safe_eval

    with pytest.raises(MathCheckError):
        safe_eval(expr)


def _with_wrong_ohm_result(result="6"):
    plan = json.loads(GOOD_JSON)
    scene = plan["scenes"][3]
    scene["narration"] = ("Let's test a 230 volt socket powering an iron box with 46 ohms resistance. "
                          f"Dividing 230 by 46 gives {result} amperes of current.")
    scene["visual"]["params"]["labels"][-1] = f"Result: I = {result} A"
    scene["check"]["result"] = result
    return plan


def test_wrong_result_is_replaced_everywhere(fake):
    fake(json.dumps(_with_wrong_ohm_result("6")))
    plan, tel = planner.plan_lesson("Ohm's Law")
    scene = plan.scenes[3]
    assert tel["math"]["status"] == "fixed" and tel["fallback_used"] is False and tel["attempt"] == 1
    assert scene.narration.endswith("gives five amperes of current.")
    assert scene.visual.params.labels[-1] == "Result: I = 5 A"
    assert scene.check.result == "5"


def test_wrong_result_written_in_words_is_replaced(fake):
    plan = json.loads(GOOD_JSON)
    scene = plan["scenes"][3]
    scene["check"] = {"expr": "100 * (1 + 0.05) ** 10", "result": "425"}
    scene["narration"] = ("Save one hundred rupees at five percent interest for ten years, "
                          "and the amount grows to four hundred twenty-five rupees.")
    fake(json.dumps(plan))
    result, tel = planner.plan_lesson("Compound Interest")
    assert tel["math"]["status"] == "fixed" and tel["math"]["computed"] == pytest.approx(162.8895)
    assert result.scenes[3].narration.endswith(
        "grows to one hundred sixty-two point eight nine rupees.")


def test_correct_result_within_tolerance_is_kept(fake):
    plan = json.loads(GOOD_JSON)
    plan["scenes"][3]["check"] = {"expr": "100 * (1 + 0.05) ** 10", "result": "163"}  # 0.07 % off
    fake(json.dumps(plan))
    _, tel = planner.plan_lesson("Compound Interest")
    assert tel["math"]["status"] == "ok"


def test_photosynthesis_without_numbers_passes(fake):
    plan = json.loads(GOOD_JSON)
    scene = plan["scenes"][3]
    scene.pop("check")
    scene["narration"] = ("Inside a mango leaf, sunlight splits water, oxygen escapes through the stomata, "
                          "and carbon dioxide is built into glucose for the tree.")
    scene["visual"]["params"] = {"labels": ["Step 1: Light absorbed", "2. Water split", "3. Glucose built"],
                                 "steps": ["Oxygen released"]}
    fake(json.dumps(plan))
    _, tel = planner.plan_lesson("Photosynthesis")
    assert tel["math"]["status"] == "none" and tel["attempt"] == 1 and tel["fallback_used"] is False


def test_invented_quantities_retry_then_become_qualitative(fake):
    plan = json.loads(GOOD_JSON)
    scene = plan["scenes"][3]
    scene.pop("check")
    scene["narration"] = ("If a plant uses one hundred units of water and one hundred units of carbon dioxide, "
                          "it produces one hundred units of glucose.")
    client = fake(json.dumps(plan), json.dumps(plan))
    result, tel = planner.plan_lesson("Photosynthesis")
    assert "computes an amount but has no check" in client.calls[1]["messages"][-1]["content"]
    assert tel["attempt"] == 2 and tel["math"]["status"] == "template" and tel["fallback_used"] is False
    assert result.scenes[3].narration.startswith("Let's walk through it step by step")
    assert result.scenes[3].check is None and result.scenes[3].visual.type == "flow"


def test_unparseable_expr_retries_with_the_error(fake):
    bad = json.loads(GOOD_JSON)
    bad["scenes"][3]["check"]["expr"] = "V / R where V = 230"
    client = fake(json.dumps(bad), GOOD_JSON)
    _, tel = planner.plan_lesson("Ohm's Law")
    assert "Math check failed" in client.calls[1]["messages"][-1]["content"]
    assert tel["attempt"] == 2 and tel["math"]["status"] == "ok"


def test_check_field_is_optional_and_backward_compatible():
    plan = LessonPlan.model_validate_json(GOLDEN_JSON)  # the frozen fixture has no check anywhere
    assert all(s.check is None for s in plan.scenes)
    schema_json = LessonPlan.model_json_schema()
    assert "check" not in schema_json["$defs"]["SceneSpec"].get("required", [])


def test_short_sentence_plus_long_sentence_is_cut_at_a_clause():
    text = ("Why do mango leaves look green in Bengaluru? Because chlorophyll inside them absorbs red and blue light, "
            "reflects green light back to our eyes, and turns sunlight into food for the whole tree every day.")
    assert len(text.split()) == 35  # first sentence alone is 8 words, both together too long
    assert planner._shorten_narration(text) == (
        "Why do mango leaves look green in Bengaluru? Because chlorophyll inside them absorbs red and blue light, "
        "reflects green light back to our eyes.")


def test_check_without_any_formula_is_treated_as_invented(fake):
    plan = json.loads(GOOD_JSON)
    for scene in plan["scenes"]:  # strip every formula from the lesson, keep the worked example's check
        params = scene["visual"]["params"]
        params["labels"] = ["Monsoon winds", "Rain over land"]
        params["steps"] = ["Moist air rises"]
    plan["scenes"][3]["check"] = {"expr": "200 * 10 * 100", "result": "200000"}
    client = fake(json.dumps(plan), json.dumps(plan))
    result, tel = planner.plan_lesson("Monsoon")
    assert "this topic has no formula" in client.calls[1]["messages"][-1]["content"]
    assert tel["math"]["status"] == "template" and result.scenes[3].check is None


def test_math_failure_then_invalid_retry_keeps_attempt_one_qualitative(fake):
    plan = json.loads(GOOD_JSON)
    plan["scenes"][3]["check"]["expr"] = "V / R"  # unparseable: attempt 1 fails only on math
    retry = json.loads(GOOD_JSON)
    retry["scenes"][0]["narration"] = "Why does your phone charger get warm while charging today?"  # 10 words
    client = fake(json.dumps(plan), json.dumps(retry))
    result, tel = planner.plan_lesson("Ohm's Law")
    assert len(client.calls) == 2
    assert tel["salvaged"] is True and tel["fallback_used"] is False and tel["math"]["status"] == "template"
    assert result.scenes[0].narration.startswith("Why does your phone charger get warm while fast-charging")
    assert result.scenes[3].narration.startswith("Let's walk through it step by step")


def test_answer_shown_in_steps_is_fixed_even_when_check_result_differs(fake):
    plan = json.loads(GOOD_JSON)
    scene = plan["scenes"][3]  # live qwen2.5:7b output: three different "answers" in one scene
    scene["narration"] = ("Let's say you invest one hundred thousand rupees at a five percent annual interest rate, "
                          "compounded quarterly for five years. After five years, you'll have one hundred thirty "
                          "thousand rupees.")
    scene["visual"]["params"] = {"labels": ["P = 100,000", "r = 5%", "n = 4", "t = 5", "A = 130,000"],
                                 "steps": ["100,000 × (1 + 0.05/4)^(4×5) = 130,000"]}
    scene["check"] = {"expr": "100000 * (1 + 0.05/4) ** (4*5)", "result": "134,685.50"}
    fake(json.dumps(plan))
    result, tel = planner.plan_lesson("Compound Interest")
    s = result.scenes[3]
    assert tel["math"]["status"] == "fixed"
    assert s.narration.endswith("you'll have about one hundred twenty-eight thousand rupees.")  # rounded for speech
    assert s.visual.params.labels == ["P = 100,000", "r = 5%", "n = 4", "t = 5", "A = 128203.72"]
    assert s.visual.params.steps == ["100,000 × (1 + 0.05/4)^(4×5) = 128203.72"]
    assert s.check.result == "128203.72"
