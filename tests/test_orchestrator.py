import json
import sys
import time
from pathlib import Path

import ollama
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import cache, planner
from orchestrator.fallbacks import build_safe_fallback_lesson
from orchestrator.prompts import FEW_SHOT_MESSAGES
from orchestrator.schema import LessonPlan

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_JSON = (ROOT / "fixtures" / "golden_ohms_law.json").read_text(encoding="utf-8")

TOPICS = [
    "Photosynthesis", "Newton's Third Law", "Binary Search", "Supply and Demand", "DNA Replication",
    "Pythagoras Theorem", "Water Cycle", "Compound Interest", "Acid-Base Titration", "TCP Three-Way Handshake",
    "Indian Independence Movement", "Monsoon", "GST", "Mughal Empire", "Democracy",
    "", "x",
    "Electromagnetic Induction In Transformers",  # 41 chars
    "Supercalifragilisticexpialidociousnesses",  # 40 chars, one word
    "the quick brown fox jumps over the lazy dog and keeps on running",
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
    assert all(8 <= w <= 42 for w in words(plan))
    assert all(len(s.narration) <= 240 for s in plan.scenes)
    assert 100 <= sum(words(plan)) <= 140
    LessonPlan.model_validate_json(plan.model_dump_json())  # survives a JSON round trip


def test_fallback_keeps_acronyms():
    assert build_safe_fallback_lesson("DNA replication").scenes[0].visual.params.labels[0] == "DNA Replication"


def test_good_response_returns_plan_and_caches(fake):
    client = fake(GOLDEN_JSON)
    plan, tel = planner.plan_lesson("Ohm's Law")
    assert tel["fallback_used"] is False and tel["attempt"] == 1 and tel["total_words"] == 122
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
    fake("{", GOLDEN_JSON)
    _, tel = planner.plan_lesson("Ohm's Law")
    assert tel["fallback_used"] is False and tel["attempt"] == 2


def test_daemon_down_falls_back_without_crashing(fake):
    client = fake(ConnectionError("refused"), ConnectionError("refused"))
    plan, tel = planner.plan_lesson("Monsoon")
    assert tel["fallback_used"] is True and len(tel["errors"]) == 2
    assert all(m["role"] != "assistant" or m in FEW_SHOT_MESSAGES for m in client.calls[1]["messages"])


@pytest.mark.parametrize("model", ["qwen3:4b", "gemma4:e4b"])
def test_thinking_models_get_think_false(fake, model):
    client = fake(GOLDEN_JSON)
    planner.plan_lesson("Ohm's Law", model=model)
    assert client.calls[0]["think"] is False


def test_model_rejecting_think_is_retried_without_flag(fake):
    client = fake(ollama.ResponseError('"gemma2" does not support thinking'), GOLDEN_JSON)
    _, tel = planner.plan_lesson("Ohm's Law", model="gemma2:2b")
    assert tel["fallback_used"] is False and tel["attempt"] == 1
    assert client.calls[0]["think"] is False and "think" not in client.calls[1]


def test_model_name_comes_from_env(monkeypatch):
    import importlib
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    try:
        assert importlib.reload(planner).MODEL_NAME == "llama3.2:3b"
    finally:
        monkeypatch.delenv("OLLAMA_MODEL")
        importlib.reload(planner)


def test_word_total_out_of_target_retries_then_keeps_safe_plan(fake):
    short = LessonPlan.model_validate_json(GOLDEN_JSON)
    short.scenes = short.scenes[:4]  # 82 words after the next line: valid schema, below target, still safe
    short.scenes[3].narration = "Dividing 230 Volts by 46 Ohms gives 5 Amperes."
    payload = short.model_dump_json()
    client = fake(payload, payload)
    plan, tel = planner.plan_lesson("Ohm's Law")
    assert len(client.calls) == 2 and "must be 100-140 words" in client.calls[1]["messages"][-1]["content"]
    assert tel["fallback_used"] is False and tel["total_words"] < 100


def test_cache_hit_under_5ms(fake):
    cache.save_plan("Ohm's Law", LessonPlan.model_validate_json(GOLDEN_JSON))
    fake()  # any LLM call would pop from an empty queue and fail
    t0 = time.perf_counter()
    plan, tel = planner.plan_lesson("  OHM'S LAW ")
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert tel["cache_hit"] is True and len(plan.scenes) == 5
    assert elapsed_ms < 5, f"cache hit took {elapsed_ms:.2f} ms"


def test_corrupt_cache_file_is_ignored(fake):
    cache.PLAN_DIR.mkdir(parents=True)
    (cache.PLAN_DIR / "monsoon.json").write_text("{broken", encoding="utf-8")
    assert cache.load_plan("Monsoon") is None


def test_stub_pipeline_timing_matches_blueprint(tmp_path):
    import wave

    import run_pipeline

    plan = LessonPlan.model_validate_json(GOLDEN_JSON)
    wav = tmp_path / "a.wav"
    manifest = run_pipeline.StubTTSEngine().synthesize_all_scenes(plan.scenes, "en", str(wav))
    assert [m["duration_sec"] for m in manifest] == [9.915, 12.089, 10.785, 12.524, 9.48]
    assert manifest[-1]["end_sec"] == pytest.approx(54.79, abs=0.01)
    with wave.open(str(wav)) as w:
        assert w.getnframes() / w.getframerate() == pytest.approx(54.79, abs=0.01)


def test_retry_names_the_overlong_scene(fake):
    plan = json.loads(GOLDEN_JSON)
    plan["scenes"][2]["narration"] = " ".join(["word"] * 45)
    client = fake(json.dumps(plan), GOLDEN_JSON)
    _, tel = planner.plan_lesson("Ohm's Law")
    feedback = client.calls[1]["messages"][-1]["content"]
    assert "Scene 3 narration" in feedback and "18-28 words" in feedback
    assert tel["attempt"] == 2 and tel["fallback_used"] is False


GRAMMAR_CUT = ("The formula for Compound Interest is A equals P times (1 plus r over n) to the power of nt, where A is "
               "the final amount, P is the principal, r is the annual interest rate, n is the number of times interest "
               "is compounded per year, and t is a")


def test_overlong_single_sentence_is_cut_at_main_clause():
    assert planner._shorten_narration(GRAMMAR_CUT) == (
        "The formula for Compound Interest is A equals P times (1 plus r over n) to the power of nt.")


def test_overlong_narration_keeps_whole_sentences():
    text = "Interest grows on interest. " + " ".join(["more"] * 40) + "."
    assert planner._shorten_narration(text) == "Interest grows on interest."


def test_repaired_plan_is_used_without_retry(fake):
    plan = json.loads(GOLDEN_JSON)
    plan["scenes"][2]["narration"] = GRAMMAR_CUT
    client = fake(json.dumps(plan))
    result, tel = planner.plan_lesson("Compound Interest")
    assert len(client.calls) == 1 and tel["repaired"] is True and tel["fallback_used"] is False
    assert result.scenes[2].narration.endswith("power of nt.")


def test_unrepairable_narration_still_retries(fake):
    plan = json.loads(GOLDEN_JSON)
    plan["scenes"][2]["narration"] = " ".join(["word"] * 45)  # no sentence or clause break to cut at
    client = fake(json.dumps(plan), json.dumps(plan))
    _, tel = planner.plan_lesson("Ohm's Law")
    assert len(client.calls) == 2 and tel["fallback_used"] is True


def test_device_env(monkeypatch):
    from orchestrator.device import get_device

    monkeypatch.setenv("DEVICE", "CPU")
    assert get_device() == "cpu"
    monkeypatch.setenv("DEVICE", "cuda")
    assert get_device() in ("cuda", "cpu")  # cpu when torch/CUDA is missing
    monkeypatch.setenv("DEVICE", "tpu")
    with pytest.raises(ValueError):
        get_device()
