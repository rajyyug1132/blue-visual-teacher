"""Plan a fixed set of topics with the live model and print a telemetry table.

    python -m orchestrator.bench                                   # model from OLLAMA_MODEL (default qwen2.5:7b)
    python -m orchestrator.bench --models qwen2.5:7b qwen2.5:3b    # compare models, pick the best
    python -m orchestrator.bench --topics "GST" "Monsoon"

Bypasses the plan cache so every topic hits the LLM. The math column is the worked-example verdict:
ok = the model's own check was right · fixed = wrong result replaced · none = no arithmetic in the lesson ·
template = unverifiable example swapped for a qualitative one · - = fallback lesson.
Each topic also prints its worked-example narration so invented quantities can be spotted by eye.
"""
import argparse
import statistics
import time

from orchestrator.planner import MODEL_NAME, plan_lesson, warm_up_ollama
from orchestrator.schema import TOTAL_MAX, TOTAL_MIN

DEFAULT_TOPICS = ["Photosynthesis", "Newton's Third Law", "Compound Interest", "Monsoon", "TCP Three-Way Handshake"]


def bench(model: str, topics: list[str]) -> dict:
    t0 = time.perf_counter()
    warm_up_ollama(model)
    print(f"\nmodel {model} | warm-up {time.perf_counter() - t0:.2f}s\n")

    header = (f"{'topic':<26} {'sec':>6} {'try':>3} {'result':<8} {'math':<8} {'words':>5} {'per scene':<24} "
              f"{'out_tok':>7} {'tok/s':>6}")
    print(header)
    print("-" * len(header))
    rows = []
    for topic in topics:
        plan, tel = plan_lesson(topic, model=model, use_cache=False)
        per_scene = [len(s.narration.split()) for s in plan.scenes]
        tok_s = tel.get("output_tokens", 0) / tel["eval_sec"] if tel.get("eval_sec") else 0
        math = "-" if tel["fallback_used"] else tel.get("math", {}).get("status", "none")
        rows.append({"topic": topic, **tel, "per_scene": per_scene, "math_status": math})
        result = "FALLBACK" if tel["fallback_used"] else "valid"
        print(f"{topic[:26]:<26} {tel['total_sec']:>6.2f} {tel['attempt']:>3} {result:<8} {math:<8} "
              f"{tel['total_words']:>5} {str(per_scene):<24} {tel.get('output_tokens', 0):>7} {tok_s:>6.1f}")
        example = next((s for s in plan.scenes if s.id == 4), None)
        if example:
            check = f"  [check {example.check.expr} = {example.check.result}]" if example.check else ""
            print(f"    ex: {example.narration}{check}")
        for err in tel.get("errors", []):
            print(f"    ! {err[:150]}")

    secs = [r["total_sec"] for r in rows]
    valid = sum(not r["fallback_used"] for r in rows)
    in_target = sum(TOTAL_MIN <= r["total_words"] <= TOTAL_MAX for r in rows)
    math_ok = sum(r["math_status"] == "ok" for r in rows)
    checked = sum(r["math_status"] in ("ok", "fixed") for r in rows)
    repairs = sum(bool(r.get("repaired")) or r["math_status"] in ("fixed", "template") for r in rows)
    summary = {"model": model, "valid": valid, "math_ok": math_ok, "checked": checked, "repairs": repairs,
               "retries": sum(r.get("attempt", 1) > 1 for r in rows), "p50": statistics.median(secs)}
    print(f"\nvalid {valid}/{len(rows)} | fallback {len(rows) - valid} | math_ok {math_ok}/{checked} checked | "
          f"repairs {repairs} | words in {TOTAL_MIN}-{TOTAL_MAX}: {in_target}/{len(rows)} | "
          f"plan sec P50 {summary['p50']:.2f}, max {max(secs):.2f}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=[MODEL_NAME])
    ap.add_argument("--model", help="single model; same as --models X")
    ap.add_argument("--topics", nargs="+", default=DEFAULT_TOPICS)
    args = ap.parse_args()
    summaries = [bench(m, args.topics) for m in ([args.model] if args.model else args.models)]
    if len(summaries) > 1:
        # Most valid plans, then most self-correct math, then fewest repairs, then speed.
        ranked = sorted(summaries, key=lambda s: (-s["valid"], -s["math_ok"], s["repairs"], s["p50"]))
        print("\nmodel            valid math_ok repairs retries  p50s")
        for s in ranked:
            print(f"{s['model']:<16} {s['valid']:>5} {s['math_ok']:>7} {s['repairs']:>7} {s['retries']:>7} "
                  f"{s['p50']:>5.2f}")
        print(f"\npick: {ranked[0]['model']}")
