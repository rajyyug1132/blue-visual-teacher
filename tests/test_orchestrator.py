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
from orchestrator.spoken import shorten_narration

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_JSON = (ROOT / "fixtures" / "golden_ohms_law.json").read_text(encoding="utf-8")
GOOD_JSON = FEW_SHOT_MESSAGES[1]["content"]  # Ohm's Law as a model reply: the fixture plus a worked-example check
DESCRIPTIVE_JSON = FEW_SHOT_MESSAGES[3]["content"]  # Binary Search, policy "none": no quantities anywhere

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
    """Stands in for ollama.Client; each queued plan is returned (str content) or raised (exception).

    The topic-classify call is answered from `has_formula` without using the queue, and `calls` only records
    planning calls. An empty queue behaves like a dead daemon (ConnectionError), so the ladder can run out.
    """

    def __init__(self, *outputs, has_formula=True, patches=()):
        self.outputs = list(outputs)
        self.calls = []
        self.classify_calls = []
        self.patch_calls = []
        self.patches = list(patches)  # replies to single-string patch calls; empty -> patching fails
        self.generate_calls = []  # warm-ups and keep_alive=0 unloads
        self.has_formula = has_formula

    def generate(self, **kwargs):
        self.generate_calls.append(kwargs)

    def chat(self, **kwargs):
        if "has_formula" in json.dumps(kwargs.get("format")):
            self.classify_calls.append(kwargs)
            return self._response(json.dumps({"has_formula": self.has_formula}))
        if "scenes" not in json.dumps(kwargs.get("format")):  # a patch call: {"text": ...}
            self.patch_calls.append(kwargs)
            if not self.patches:
                raise ConnectionError("fake daemon: no patch reply queued")
            return self._response(json.dumps({"text": self.patches.pop(0)}))
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        if not self.outputs:
            raise ConnectionError("fake daemon: no more queued outputs")
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return self._response(out)

    @staticmethod
    def _response(content):
        return ollama.ChatResponse(
            model="fake", message=ollama.Message(role="assistant", content=content),
            prompt_eval_count=10, eval_count=20, eval_duration=1_000_000, load_duration=0,
        )


@pytest.fixture
def fake(monkeypatch):
    def install(*outputs, has_formula=True, escalation="", patches=()):
        client = FakeClient(*outputs, has_formula=has_formula, patches=patches)
        monkeypatch.setattr(planner, "_client", client)
        monkeypatch.setattr(planner, "ESCALATION_MODEL", escalation)  # off unless a test turns it on
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


def test_bad_json_climbs_the_whole_ladder_to_the_template(fake):
    client = fake("not json at all", '{"title": "x"}', '{"title": "y"}')
    plan, tel = planner.plan_lesson("Ohm's Law")
    assert tel["fallback_used"] is True and tel["attempt"] == 4 and tel["stage"] == "template"
    assert len(client.calls) == 3
    # The retry carries the bad output and the problems back to the model.
    retry_msgs = client.calls[1]["messages"]
    assert retry_msgs[-2] == {"role": "assistant", "content": "not json at all"}
    assert retry_msgs[-1]["content"].startswith("Problems:")
    # Qualitative mode starts a fresh conversation without the failed drafts.
    qual_msgs = client.calls[2]["messages"]
    assert "QUALITATIVE MODE" in qual_msgs[-1]["content"] and "Number policy: none" in qual_msgs[-1]["content"]
    assert all(m["content"] not in ("not json at all", '{"title": "x"}') for m in qual_msgs)
    assert cache.load_plan("Ohm's Law") is None  # fallbacks are never cached


def test_bad_json_then_good_retry(fake):
    fake("{", GOOD_JSON)
    _, tel = planner.plan_lesson("Ohm's Law")
    assert tel["fallback_used"] is False and tel["attempt"] == 2


def test_daemon_down_falls_back_without_crashing(fake):
    client = fake(ConnectionError("refused"), ConnectionError("refused"), ConnectionError("refused"))
    plan, tel = planner.plan_lesson("Monsoon")
    assert tel["fallback_used"] is True and len(tel["errors"]) == 3
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


def test_default_models_are_qwen_3b_then_7b(monkeypatch):
    import importlib
    for var in ("PLANNER_MODEL", "OLLAMA_MODEL", "PLANNER_ESCALATION_MODEL"):
        monkeypatch.delenv(var, raising=False)
    try:
        reloaded = importlib.reload(planner)
        assert (reloaded.MODEL_NAME, reloaded.ESCALATION_MODEL) == ("qwen2.5:3b", "qwen2.5:7b")
    finally:
        importlib.reload(planner)


@pytest.mark.parametrize("env, expected", [
    ({"PLANNER_MODEL": "llama3.2:3b"}, ("llama3.2:3b", "qwen2.5:7b")),
    ({"OLLAMA_MODEL": "llama3.2:3b"}, ("llama3.2:3b", "qwen2.5:7b")),  # older name still works
    ({"PLANNER_ESCALATION_MODEL": ""}, ("qwen2.5:3b", "")),  # escalation disabled
])
def test_models_come_from_env(monkeypatch, env, expected):
    import importlib
    for var in ("PLANNER_MODEL", "OLLAMA_MODEL", "PLANNER_ESCALATION_MODEL"):
        monkeypatch.delenv(var, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    try:
        reloaded = importlib.reload(planner)
        assert (reloaded.MODEL_NAME, reloaded.ESCALATION_MODEL) == expected
    finally:
        for k in env:
            monkeypatch.delenv(k)
        importlib.reload(planner)


def test_escalation_unloads_3b_runs_7b_then_restores_3b(fake):
    bad = '{"title": "x"}'
    client = fake(bad, bad, GOOD_JSON, escalation="qwen2.5:7b")
    plan, tel = planner.plan_lesson("Ohm's Law", model="qwen2.5:3b")
    assert [c["model"] for c in client.calls] == ["qwen2.5:3b", "qwen2.5:3b", "qwen2.5:7b"]
    assert tel["stage"] == "escalate" and tel["model"] == "qwen2.5:7b" and tel["fallback_used"] is False
    assert [(r["stage"], r["model"], r["ok"]) for r in tel["rungs"]] == [
        ("plan", "qwen2.5:3b", False), ("retry", "qwen2.5:3b", False), ("escalate", "qwen2.5:7b", True)]
    # 3b unloaded before 7b runs; afterwards 7b unloaded and 3b warmed again: one model in VRAM at a time.
    assert [(g["model"], g["keep_alive"]) for g in client.generate_calls] == [
        ("qwen2.5:3b", 0), ("qwen2.5:7b", 0), ("qwen2.5:3b", -1)]
    # The 7b attempt is a fresh conversation that carries the problem list, not the failed drafts.
    escalate_msgs = client.calls[2]["messages"]
    assert "rejected for these problems" in escalate_msgs[-1]["content"]
    assert all(m["content"] != bad for m in escalate_msgs)


def test_full_ladder_with_escalation_ends_on_template(fake):
    client = fake("{", "{", "{", "{", escalation="qwen2.5:7b")
    _, tel = planner.plan_lesson("Ohm's Law", model="qwen2.5:3b")
    assert [c["model"] for c in client.calls] == ["qwen2.5:3b"] * 2 + ["qwen2.5:7b"] * 2  # qualitative stays on 7b
    assert tel["stage"] == "template" and tel["attempt"] == 5 and tel["fallback_used"] is True


def test_lesson_total_below_range_retries_with_total_feedback(fake):
    short = json.loads(GOOD_JSON)
    short["scenes"] = short["scenes"][:4]
    for s in short["scenes"]:
        s["narration"] = "Voltage pushes current through a wire while resistance slows it down in every circuit."  # 14
    payload = json.dumps(short)  # every scene valid, lesson total 56 words < 85
    client = fake(payload, payload)
    _, tel = planner.plan_lesson("Ohm's Law")
    feedback = client.calls[1]["messages"][-1]["content"]
    assert "total 56 words" in feedback and "does not fill a 60s lesson" in feedback
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
    assert shorten_narration(GRAMMAR_CUT) == (
        "The formula for Compound Interest is A equals P times (one plus r over n) to the power of nt.")


def test_overlong_narration_keeps_whole_sentences():
    first = "Compound interest means the bank pays interest on your savings and also on the interest already earned."
    text = first + " " + " ".join(["more"] * 40) + "."
    assert shorten_narration(text) == first


def test_too_short_kept_sentences_are_not_used():
    text = "Interest grows on interest. " + " ".join(["more"] * 40) + "."
    assert shorten_narration(text) is None  # four words would fail the per-scene minimum


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
    client = fake(json.dumps(plan), json.dumps(plan), json.dumps(plan))
    _, tel = planner.plan_lesson("Ohm's Law")
    assert len(client.calls) == 3 and tel["fallback_used"] is True


@pytest.mark.parametrize("text, spoken", [
    ("Dividing 230 Volts by 46 Ω gives 5 A.", "Dividing two hundred thirty Volts by forty-six ohms gives five A."),
    ("Plants turn 6CO2 and 6H2O into sugar.", "Plants turn six carbon dioxide and six water into sugar."),
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


def _compound_interest(result="425", spoken_answer="four hundred twenty-five"):
    """Ohm's plan with a self-consistent compound-interest worked example in scene 4."""
    plan = json.loads(GOOD_JSON)
    scene = plan["scenes"][3]
    scene["check"] = {"expr": "100 * (1 + 0.05) ** 10", "result": result}
    scene["narration"] = ("Save one hundred rupees at five percent interest for ten years, "
                          f"and the amount grows to {spoken_answer} rupees.")
    scene["visual"]["params"] = {"labels": ["P = 100", "r = 5%", "t = 10"],
                                 "steps": [f"100 × (1 + 0.05)^10 = {result}"]}
    return plan


def test_wrong_result_written_in_words_is_replaced(fake):
    fake(json.dumps(_compound_interest()))
    result, tel = planner.plan_lesson("Compound Interest")
    assert tel["math"]["status"] == "fixed" and tel["math"]["computed"] == pytest.approx(162.8895)
    assert result.scenes[3].narration.endswith("grows to one hundred sixty-two point eight nine rupees.")
    assert result.scenes[3].visual.params.steps == ["100 × (1 + 0.05)^10 = 162.89"]


def test_correct_result_within_tolerance_is_kept(fake):
    fake(json.dumps(_compound_interest("163", "one hundred sixty-three")))  # 0.07 % off
    _, tel = planner.plan_lesson("Compound Interest")
    assert tel["math"]["status"] == "ok" and tel["attempt"] == 1


def _descriptive(narration4=None, params4=None):
    """The policy-"none" Binary Search few-shot, optionally with a different scene 4."""
    plan = json.loads(DESCRIPTIVE_JSON)
    if narration4:
        plan["scenes"][3]["narration"] = narration4
    if params4:
        plan["scenes"][3]["visual"]["params"] = params4
    return plan


def test_photosynthesis_without_numbers_passes(fake):
    fake(json.dumps(_descriptive(
        "Inside a mango leaf, sunlight splits water, oxygen escapes through the stomata, "
        "and carbon dioxide is built into glucose for the tree.",
        {"labels": ["Step 1: Light absorbed", "2. Water split", "3. Glucose built"], "steps": ["Oxygen released"]})),
        has_formula=False)
    _, tel = planner.plan_lesson("Photosynthesis")
    assert tel["policy"] == "none" and tel["stage"] == "plan" and tel["fallback_used"] is False


def test_invented_quantities_retry_then_qualitative_mode(fake):
    invented = json.dumps(_descriptive(
        "If a plant uses one hundred units of water and one hundred units of carbon dioxide, "
        "it produces one hundred units of glucose."))
    client = fake(invented, invented, DESCRIPTIVE_JSON, has_formula=False)
    result, tel = planner.plan_lesson("Photosynthesis")
    assert "Remove the numbers (100, 100, 100) from scene 4 narration" in client.calls[1]["messages"][-1]["content"]
    assert "QUALITATIVE MODE" in client.calls[2]["messages"][-1]["content"]
    assert tel["stage"] == "qualitative" and tel["attempt"] == 3 and tel["fallback_used"] is False
    assert all(s.check is None for s in result.scenes)


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
    assert shorten_narration(text) == (
        "Why do mango leaves look green in Bengaluru? Because chlorophyll inside them absorbs red and blue light, "
        "reflects green light back to our eyes.")


def test_math_failing_twice_regenerates_in_qualitative_mode(fake):
    plan = json.loads(GOOD_JSON)
    plan["scenes"][3]["check"]["expr"] = "V / R"  # names are rejected by the AST whitelist
    client = fake(json.dumps(plan), json.dumps(plan), DESCRIPTIVE_JSON)
    result, tel = planner.plan_lesson("Ohm's Law")
    assert "Math check failed" in client.calls[1]["messages"][-1]["content"]
    assert tel["stage"] == "qualitative" and tel["policy"] == "none" and tel["fallback_used"] is False


def test_classify_failure_means_policy_none(fake, monkeypatch):
    client = fake(DESCRIPTIVE_JSON)
    monkeypatch.setattr(client, "has_formula", "maybe")  # anything but a JSON true
    _, tel = planner.plan_lesson("Monsoon")
    assert tel["policy"] == "none" and len(client.classify_calls) == 1
    assert "Number policy: none" in client.calls[0]["messages"][-1]["content"]
    assert client.classify_calls[0]["options"]["num_ctx"] == client.calls[0]["options"]["num_ctx"]  # no reload


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


# --- duration fit: over-long (usually Kannada) audio is trimmed, not rejected -----------------------------------

class SlowTTS:
    """1 second per word + 0.35 s tail: long enough that the Ohm's lesson (123 words) runs ~125 s."""

    def __init__(self):
        self.calls = 0

    def synthesize_all_scenes(self, scenes, lang, out_wav_path):
        self.calls += 1
        timing, cursor = [], 0.0
        for s in scenes:
            dur = len(s.narration.split()) + 0.35
            timing.append({"id": s.id, "start_sec": cursor, "end_sec": cursor + dur, "duration_sec": dur,
                           "narration": s.narration, "visual": s.visual.model_dump()})
            cursor += dur
        return timing


def test_fit_duration_trims_ordinary_scenes_then_recap_and_keeps_the_answer(tmp_path):
    from orchestrator.pipeline import DURATION_MAX_SEC, fit_duration

    plan = LessonPlan.model_validate_json(GOOD_JSON)  # scene 4 carries the check and the spoken answer
    tts = SlowTTS()
    timing, trims = fit_duration(plan, tts.synthesize_all_scenes(plan.scenes, "kn", None), tts, "kn", tmp_path)
    assert timing[-1]["end_sec"] <= DURATION_MAX_SEC, (timing[-1]["end_sec"], trims)
    assert trims == ["scene 2: dropped last sentence", "scene 3: dropped last sentence", "scene 5: cut (recap)"]
    assert plan.scenes[3].narration.endswith("gives five amperes of current.")  # the answer survived
    assert len(plan.scenes) == 4 and [t["narration"] for t in timing] == [s.narration for s in plan.scenes]


def test_generate_lesson_fits_long_audio_and_leaves_the_cached_plan_alone(tmp_path, monkeypatch):
    from orchestrator import pipeline

    monkeypatch.setattr(pipeline, "ARTIFACTS", tmp_path)
    plan = LessonPlan.model_validate_json(GOOD_JSON)
    exported = []
    out = pipeline.generate_lesson("Ohm's Law", "kn", tts=SlowTTS(), translator=type("T", (), {
        "localize_lesson": lambda self, p, lang: p})(), plan_fn=lambda topic: (plan, {}),
        export=lambda d, lang, cb: exported.append(d))
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    tel = json.loads((out / "telemetry.json").read_text(encoding="utf-8"))
    assert manifest["total_sec"] <= 90 and len(manifest["scenes"]) == 4 and exported == [out]
    assert len(tel["planner"]["duration_trims"]) == 3 and "duration_fit" in tel["stage_sec"]
    assert len(plan.scenes) == 5  # the shared English plan was not modified
    english = {s.id: s for s in plan.scenes}
    for scene in manifest["scenes"]:  # the renderer's English illustration hint, matched by scene id
        hint = scene["visual"]["params"]["topic_en"]
        assert hint.startswith(plan.title) and english[scene["id"]].visual.params.labels[0] in hint


# --- CC-2 part 2: learner level and target length (Stage 1 inputs) -------------------------------------------

def _narration(words_n: int) -> str:
    return " ".join(["voltage"] * words_n)


def _scenes(lengths: list[int]) -> list[dict]:
    return [{"id": i + 1, "narration": _narration(n),
             "visual": {"type": "title", "params": {"labels": ["Ohm's Law"], "steps": ["Voltage and current"]}}}
            for i, n in enumerate(lengths)]


@pytest.mark.parametrize("target,lengths", [(30, [17, 17, 17, 17]), (45, [20] * 5),
                                            (60, [27] * 5), (75, [29] * 6), (90, [32] * 6)])
def test_target_sec_sets_the_word_budget(target, lengths):
    plan = LessonPlan.model_validate({"title": "Voltage and current", "target_sec": target,
                                      "scenes": _scenes(lengths)})
    assert plan.target_sec == target and plan.level == "beginner"
    golden = json.loads(GOLDEN_JSON)  # 123 words, ~55 s
    if target in (30, 45):  # longer than the request allows: still rejected
        with pytest.raises(ValidationError, match=rf"does not fill a {target}s lesson"):
            LessonPlan.model_validate({**golden, "target_sec": target})
    else:  # at least 60% of the request: a real short lesson is accepted instead of falling back to the template
        LessonPlan.model_validate({**golden, "target_sec": target})


def test_a_short_real_lesson_is_kept_but_a_far_too_short_one_is_not():
    # 90 s asked: 6 x 20 words (~54 s) passes the 60% floor; 6 x 14 words (~39 s) does not
    LessonPlan.model_validate({"title": "Voltage and current", "target_sec": 90, "scenes": _scenes([20] * 6)})
    with pytest.raises(ValidationError, match=r"does not fill a 90s lesson"):
        LessonPlan.model_validate({"title": "Voltage and current", "target_sec": 90, "scenes": _scenes([14] * 6)})


def test_a_request_is_cleaned_down_to_its_topic():
    assert planner.clean_topic("teach me java script") == "JavaScript"
    assert planner.clean_topic("Can you explain recursion?") == "recursion"
    assert planner.clean_topic("What is photosynthesis") == "photosynthesis"
    assert planner.clean_topic("Ohm's Law") == "Ohm's Law"
    assert planner.clean_topic("teach me") == "teach me"  # nothing left: keep what was typed


def test_code_scene_slips_are_repaired_not_fatal():
    scenes = [
        {"visual": {"type": "code_walkthrough", "params": {"code": ["let s = 0", "for (x of xs) s += x", "log(s)"],
                    "trace": [{"line": 0, "vars": [{"name": "s", "value": 0}]}, {"line": 9, "vars": []}]}}},
        {"visual": {"type": "code_walkthrough", "params": {"labels": ["Loop"], "steps": ["Repeat"]}}},
        {"visual": {"type": "bullets", "params": {"labels": ["Recap"], "code": ["x"], "trace": [{"line": 1}]}}},
    ]
    assert planner._repair_code_scenes(scenes) is True
    first = scenes[0]["visual"]["params"]
    assert [s["line"] for s in first["trace"]] == [1]  # 0-based shifted to 1-based; line 10 dropped
    assert first["trace"][0]["vars"] == [{"name": "s", "value": "0"}]  # values become strings
    assert scenes[1]["visual"]["type"] == "flow" and "code" not in scenes[1]["visual"]["params"]
    assert "code" not in scenes[2]["visual"]["params"] and "trace" not in scenes[2]["visual"]["params"]


def test_programming_topics_must_get_a_code_walkthrough():
    from orchestrator.prompts import is_programming_topic, request

    assert "MUST use visual type \"code_walkthrough\"" in request("Python for loops", "none")
    assert "code_walkthrough" not in request("Ohm's Law", "checked").splitlines()[-1]
    assert [is_programming_topic(t) for t in ("Recursion", "Binary Search", "String theory", "Quadratic function")] \
        == [True, True, False, False]


def test_check_result_written_in_words_is_read_as_a_number():
    from orchestrator import mathcheck

    right = _with_wrong_ohm_result("5")
    right["scenes"][3]["check"]["result"] = "five"  # the model spelled the answer out
    assert mathcheck.verify_plan(right)["status"] == "ok"
    wrong = _with_wrong_ohm_result("6")
    wrong["scenes"][3]["check"]["result"] = "six"
    assert mathcheck.verify_plan(wrong)["status"] == "fixed"


def test_level_and_length_are_in_the_plan_cache_key(tmp_path):
    default = LessonPlan.model_validate(json.loads(GOLDEN_JSON))
    other = LessonPlan.model_validate({"title": "Voltage and current", "level": "intermediate", "target_sec": 45,
                                       "scenes": _scenes([20] * 5)})
    path_default = cache.save_plan("Ohm's Law", default, plan_dir=tmp_path)
    path_other = cache.save_plan("Ohm's Law", other, plan_dir=tmp_path)
    assert path_default.name == "ohm-s-law.json"
    assert path_other.name == "ohm-s-law__intermediate__45s.json"
    assert cache.load_plan("Ohm's Law", plan_dir=tmp_path) == default
    assert cache.load_plan("Ohm's Law", plan_dir=tmp_path, level="intermediate", target_sec=45) == other
    assert cache.load_plan("Ohm's Law", plan_dir=tmp_path, level="beginner", target_sec=45) is None


def test_request_states_level_and_length():
    from orchestrator.prompts import request

    beginner = request("Ohm's Law", "checked", "beginner", 30)
    advanced = request("Ohm's Law", "checked", "intermediate", 90)
    assert "Learner level: beginner" in beginner and "exactly 4 scenes" in beginner and "30 seconds" in beginner
    assert "Learner level: intermediate" in advanced and "exactly 6 scenes" in advanced and "90 seconds" in advanced


def test_plan_lesson_uses_the_requested_level_and_length(fake):
    payload = json.dumps({"title": "Voltage and current", "scenes": _scenes([17, 17, 17, 17])})
    client = fake(payload, has_formula=False)  # no numbers, so the qualitative audit is satisfied
    plan, tel = planner.plan_lesson("Ohm's Law", level="beginner", target_sec=30)
    assert (plan.level, plan.target_sec) == ("beginner", 30)
    assert (tel["level"], tel["target_sec"]) == ("beginner", 30)
    assert "Lesson length: 30 seconds" in client.calls[0]["messages"][-1]["content"]
    assert cache.load_plan("Ohm's Law", target_sec=30) == plan  # cached under the 30 s key
    assert cache.load_plan("Ohm's Law") is None  # and not under the default one


def test_artifact_dir_and_cache_are_keyed_by_level_and_length(tmp_path, monkeypatch):
    from orchestrator import pipeline

    monkeypatch.setattr(pipeline, "ARTIFACTS", tmp_path)
    assert pipeline.artifact_dir("Ohm's Law", "hi").name == "ohm-s-law_hi"
    assert pipeline.artifact_dir("Ohm's Law", "hi", "intermediate", 90).name == "ohm-s-law_hi__intermediate__90s"
    assert pipeline.artifact_dir("Ohm's Law", "hi", "beginner", 45).name == "ohm-s-law_hi__beginner__45s"
    cached = tmp_path / "ohm-s-law_hi"
    cached.mkdir()
    (cached / "manifest.json").write_text("{}", encoding="utf-8")
    (cached / "lesson.mp4").write_bytes(b"x")
    assert pipeline.cached_artifact("Ohm's Law", "hi") == cached
    assert pipeline.cached_artifact("Ohm's Law", "hi", "beginner", 45) is None  # a 60 s lesson is not a 45 s one


@pytest.mark.parametrize("target", [30, 45, 60, 75, 90])
def test_fallback_fills_the_requested_length(target):
    plan = build_safe_fallback_lesson("Photosynthesis", "beginner", target)
    lo, hi = schema.word_band(target, len(plan.scenes))
    assert plan.target_sec == target
    assert lo <= sum(words(plan)) <= hi
    assert all(schema.WORDS_MIN <= w <= schema.WORDS_MAX for w in words(plan))


def test_available_languages_reports_kannada_tamil_bengali(monkeypatch):
    """en/hi stay off unless the fake says so; kn, ta, bn come from mms_models. te is not a language."""
    from orchestrator import pipeline

    class TTS:
        kokoro_en = None
        kokoro_hi = None
        mms_models = {"kn": object(), "ta": object(), "bn": object()}

    class Translator:
        model = object()

    monkeypatch.setattr(pipeline, "warmup", lambda planner=False: {"tts": TTS(), "translator": Translator()})
    assert pipeline.available_languages() == ["kn", "ta", "bn"]


def test_generate_lesson_fails_on_tone_audio(tmp_path, monkeypatch):
    import numpy as np
    import wave
    from orchestrator import pipeline
    from orchestrator.schema import LessonPlan

    monkeypatch.setattr(pipeline, "ARTIFACTS", tmp_path)
    plan = LessonPlan.model_validate_json(GOOD_JSON)

    class ToneTTS:
        def synthesize_all_scenes(self, scenes, lang, out_wav_path):
            sr = 24000
            dur = 35.0
            n_samples = int(dur * sr)
            t = np.linspace(0, dur, n_samples, endpoint=False)
            audio = (0.90 * np.sin(2 * np.pi * 440.0 * t) * 32767).astype(np.int16)
            with wave.open(str(out_wav_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(audio.tobytes())
            timing, cursor = [], 0.0
            for s in scenes:
                sdur = dur / len(scenes)
                timing.append({"id": s.id, "start_sec": cursor, "end_sec": cursor + sdur, "duration_sec": sdur,
                               "narration": s.narration, "visual": s.visual.model_dump()})
                cursor += sdur
            return timing

    with pytest.raises(RuntimeError, match="non-speech audio"):
        pipeline.generate_lesson(
            "Ohm's Law",
            "en",
            tts=ToneTTS(),
            plan_fn=lambda topic: (plan, {}),
            export=lambda d, lang, cb: None,
        )
    # Ensure tone audio was not left behind in artifacts
    assert not (tmp_path / "ohm-s-law_en" / "lesson_audio.wav").exists()
    assert not (tmp_path / "ohm-s-law_en" / "manifest.json").exists()
