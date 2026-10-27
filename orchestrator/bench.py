"""Plan topics with the live model and print a telemetry table plus the numeric-guard acceptance checks.

    python -m orchestrator.bench                                   # 5 topics, model from OLLAMA_MODEL
    python -m orchestrator.bench --stress                          # the 20-topic set from PLAN.md section 7
    python -m orchestrator.bench --stress --models qwen2.5:3b qwen2.5:7b
    python -m orchestrator.bench --topics "GST" "Monsoon"

Bypasses the plan cache so every topic hits the LLM. Columns:
policy   classify result (checked = has a formula, none = descriptive)
stage    rung of the ladder that produced the plan: plan · retry · escalate · qualitative · template (= fallback)
model    model of that rung (escalate and qualitative run on PLANNER_ESCALATION_MODEL when it is set)
sec      what the student waits for this plan; swap = extra seconds unloading 7b and re-warming 3b afterwards
math     ok = the model's own check was right · fixed = wrong result replaced · none = no check
said     worked example speaks its verified answer (y/n, - when there is no check)
viol     guard violations raised on the way (each sent back to the model), then the final-plan audit
Acceptance (from the review): >= 19/20 without the template, no digits or "=" in descriptive topics, every
worked example speaks its answer. Each topic's scene-4 narration is printed so invented facts can be spotted by eye.
"""
import argparse
import statistics
import time

from orchestrator.numeric_guard import audit_numbers, close, nfkc, spoken_numbers
from orchestrator.planner import MODEL_NAME, plan_lesson, warm_up_ollama

DEFAULT_TOPICS = ["Photosynthesis", "Newton's Third Law", "Compound Interest", "Monsoon", "TCP Three-Way Handshake"]
STRESS_TOPICS = [
    "Photosynthesis", "Newton's Third Law", "Binary Search", "Supply and Demand", "DNA Replication",
    "Pythagoras Theorem", "Water Cycle", "Compound Interest", "Acid-Base Titration", "TCP Three-Way Handshake",
    "Indian Independence Movement", "Monsoon", "GST", "Mughal Empire", "Democracy",
    "Green Revolution", "Mauryan Empire", "Fundamental Rights", "Climate Change", "Panchayati Raj",
]


def final_checks(plan, tel) -> tuple[list[str], str]:
    """Acceptance checks on the plan that would ship: (problems, answer-spoken flag)."""
    policy = tel.get("policy", "none")
    math = tel.get("math", {})
    data = plan.model_dump()
    problems = audit_numbers(data, policy, set(math.get("allowed", [])))
    if policy == "none":
        shown = [t for s in data["scenes"] for t in s["visual"]["params"]["labels"] + s["visual"]["params"]["steps"]]
        if any("=" in nfkc(t) for t in shown + [s["narration"] for s in data["scenes"]]):
            problems.append("'=' in a descriptive topic")
    said = "-"
    if math.get("result") is not None:
        scene = next(s for s in plan.scenes if s.id == math["scene"])
        said = "y" if any(close(v, math["result"]) for v in spoken_numbers(scene.narration)) else "n"
        if said == "n":
            problems.append("worked example does not speak its answer")
    return problems, said


def bench(model: str, topics: list[str]) -> dict:
    t0 = time.perf_counter()
    warm_up_ollama(model)
    print(f"\nmodel {model} | warm-up {time.perf_counter() - t0:.2f}s\n")

    header = (f"{'topic':<28} {'sec':>6} {'swap':>5} {'cls':>5} {'policy':<7} {'stage':<11} {'model':<11} "
              f"{'math':<6} {'said':<4} {'viol':>4} {'final':<5} {'words':>5}")
    print(header)
    print("-" * len(header))
    rows = []
    for topic in topics:
        plan, tel = plan_lesson(topic, model=model, use_cache=False)
        problems, said = final_checks(plan, tel)
        raised = sum(e.count(" | ") + 1 for e in tel.get("errors", []))
        row = {"topic": topic, **tel, "said": said, "final_problems": problems, "raised": raised}
        rows.append(row)
        print(f"{topic[:28]:<28} {tel['total_sec']:>6.2f} {tel.get('swap_sec', 0):>5.1f} "
              f"{tel.get('classify_sec', 0):>5.2f} {tel.get('policy', '?'):<7} {tel.get('stage', '?'):<11} "
              f"{tel.get('model') or '-':<11} {tel.get('math', {}).get('status', '-'):<6} "
              f"{said:<4} {raised:>4} {'ok' if not problems else 'FAIL':<5} {tel['total_words']:>5}")
        if len(tel.get("rungs", [])) > 1:
            print("    rungs: " + " -> ".join(f"{r['stage']} {r['model']} {r['sec']}s {'ok' if r['ok'] else 'x'}"
                                         for r in tel["rungs"]))
        example = next((s for s in plan.scenes if s.id == 4), None)
        if example:
            check = f"  [check {example.check.expr} = {example.check.result}]" if example.check else ""
            print(f"    ex: {example.narration}{check}")
        for err in tel.get("errors", []):
            print(f"    ! {err[:160]}")
        for p in problems:
            print(f"    X {p[:160]}")

    secs = [r["total_sec"] for r in rows]
    summary = {
        "model": model,
        "valid": sum(not r["fallback_used"] for r in rows),
        "templates": sum(r["fallback_used"] for r in rows),
        "qualitative": sum(str(r.get("stage")).split("+")[0] == "qualitative" for r in rows),
        "escalated": sum(str(r.get("stage")).split("+")[0] == "escalate" for r in rows),
        "retries": sum(str(r.get("stage")).split("+")[0] == "retry" for r in rows),
        "first_try": sum(str(r.get("stage")).split("+")[0] == "plan" for r in rows),
        "patched": sum(str(r.get("stage")).endswith("+patch") for r in rows),
        "raised": sum(r["raised"] for r in rows),
        "final_fail": sum(bool(r["final_problems"]) for r in rows),
        "math_ok": sum(r.get("math", {}).get("status") == "ok" for r in rows),
        "math_fixed": sum(r.get("math", {}).get("status") == "fixed" for r in rows),
        "unspoken": sum(r["said"] == "n" for r in rows),
        "hooks": sum(bool(r.get("hook_extended")) for r in rows),
        "p50": statistics.median(secs), "p90": sorted(secs)[max(0, int(len(secs) * 0.9) - 1)], "max": max(secs),
        "n": len(rows),
    }
    s = summary
    print(f"\nvalid {s['valid']}/{s['n']} (patched {s['patched']}; first try {s['first_try']}, retry {s['retries']}, escalate "
          f"{s['escalated']}, qualitative {s['qualitative']}, template {s['templates']}) | "
          f"violations raised {s['raised']} | final-plan failures {s['final_fail']} | "
          f"math ok {s['math_ok']} fixed {s['math_fixed']} | unspoken answers {s['unspoken']} | "
          f"short hooks extended {s['hooks']} | plan sec P50 {s['p50']:.1f} P90 {s['p90']:.1f} max {s['max']:.1f}")
    accept = s["valid"] >= s["n"] - max(1, s["n"] // 20) and s["final_fail"] == 0
    print(f"acceptance: {'PASS' if accept else 'FAIL'}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=[MODEL_NAME])
    ap.add_argument("--model", help="single model; same as --models X")
    ap.add_argument("--topics", nargs="+")
    ap.add_argument("--stress", action="store_true", help="the 20-topic set from PLAN.md section 7")
    args = ap.parse_args()
    topics = args.topics or (STRESS_TOPICS if args.stress else DEFAULT_TOPICS)
    summaries = [bench(m, topics) for m in ([args.model] if args.model else args.models)]
    if len(summaries) > 1:
        print("\nmodel            valid templ qual  viol final_fail unspoken  p50s  p90s")
        for s in summaries:
            print(f"{s['model']:<16} {s['valid']:>5} {s['templates']:>5} {s['qualitative']:>4} {s['raised']:>5} "
                  f"{s['final_fail']:>10} {s['unspoken']:>8} {s['p50']:>5.1f} {s['p90']:>5.1f}")
