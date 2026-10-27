"""Plan a fixed set of topics with the live model and print a telemetry table.

    python -m orchestrator.bench                          # model from OLLAMA_MODEL (default qwen2.5:3b)
    python -m orchestrator.bench --model llama3.2:3b      # compare another model
    python -m orchestrator.bench --topics "GST" "Monsoon"

Bypasses the plan cache so every topic hits the LLM.
"""
import argparse
import statistics
import time

from orchestrator.planner import MODEL_NAME, TARGET_WORDS, plan_lesson, warm_up_ollama

DEFAULT_TOPICS = ["Photosynthesis", "Newton's Third Law", "Compound Interest", "Monsoon", "TCP Three-Way Handshake"]


def bench(model: str, topics: list[str]) -> list[dict]:
    t0 = time.perf_counter()
    warm_up_ollama(model)
    print(f"model {model} | warm-up {time.perf_counter() - t0:.2f}s\n")

    header = f"{'topic':<26} {'sec':>6} {'try':>3} {'result':<8} {'words':>5} {'per scene':<22} {'out_tok':>7} {'tok/s':>6}"
    print(header)
    print("-" * len(header))
    rows = []
    for topic in topics:
        plan, tel = plan_lesson(topic, model=model, use_cache=False)
        per_scene = [len(s.narration.split()) for s in plan.scenes]
        tok_s = tel.get("output_tokens", 0) / tel["eval_sec"] if tel.get("eval_sec") else 0
        rows.append({"topic": topic, **tel, "per_scene": per_scene})
        result = "FALLBACK" if tel["fallback_used"] else "valid"
        print(f"{topic[:26]:<26} {tel['total_sec']:>6.2f} {tel['attempt']:>3} {result:<8} {tel['total_words']:>5} "
              f"{str(per_scene):<22} {tel.get('output_tokens', 0):>7} {tok_s:>6.1f}")
        for err in tel.get("errors", []):
            print(f"    ! {err[:150]}")

    secs = [r["total_sec"] for r in rows]
    valid = sum(not r["fallback_used"] for r in rows)
    in_target = sum(TARGET_WORDS[0] <= r["total_words"] <= TARGET_WORDS[1] for r in rows)
    print(f"\nvalid {valid}/{len(rows)} | fallback {len(rows) - valid} | "
          f"words in {TARGET_WORDS[0]}-{TARGET_WORDS[1]}: {in_target}/{len(rows)} | "
          f"plan sec P50 {statistics.median(secs):.2f}, max {max(secs):.2f}")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=MODEL_NAME)
    ap.add_argument("--topics", nargs="+", default=DEFAULT_TOPICS)
    args = ap.parse_args()
    bench(args.model, args.topics)
