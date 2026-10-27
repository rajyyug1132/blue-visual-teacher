"""BLUEPRINT DONE checks D1-D10. Each check writes its evidence to logs/D#.log; the summary goes to logs/summary.md.

    python -m orchestrator.done_checks            # all checks
    python -m orchestrator.done_checks D1 D3      # some checks
    python -m orchestrator.done_checks --skip-slow # skip the live-LLM 20-topic run (D2) and the 60-video export (D7)

States: PASS · FAIL (ran, criteria not met) · MISSING (deliverable not in the repo yet) · BLOCKED (needs a model,
package or human step that is not available here; the log says which).
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
OWNERS = {"D1": "YYUG", "D2": "YYUG", "D3": "YYUG", "D4": "TARUN", "D5": "TARUN", "D6": "FARHAN",
          "D7": "AYUSH", "D8": "AYUSH", "D9": "ALL", "D10": "AYUSH"}
TITLES = {"D1": "schema + golden fixture", "D2": "planner ladder, 20 topics", "D3": "plan + artifact cache",
          "D4": "IndicTrans2 + IndicProcessor", "D5": "TTS 24 kHz, deterministic", "D6": "renderer 8 templates",
          "D7": "export 20 topics x en/hi/kn", "D8": "web UI", "D9": "pytest incl. offline e2e",
          "D10": "README, run_demo.sh, pre-cache"}


class Result:
    def __init__(self, state: str, detail: str, log: list[str]):
        self.state, self.detail, self.log = state, detail, log


def _run(cmd: list[str], timeout: int = 3600, env: dict | None = None) -> tuple[int, str]:
    import os
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, env={**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})})
    return proc.returncode, proc.stdout + proc.stderr


def d1() -> Result:
    from orchestrator.schema import LessonPlan
    expected = [22, 27, 24, 29, 21]  # CC-1: scene 4 spelled out in words (28 -> 29), agreed by YYUG
    raw = (ROOT / "fixtures" / "golden_ohms_law.json").read_text(encoding="utf-8")
    plan = LessonPlan.model_validate_json(raw)
    words = [len(s.narration.split()) for s in plan.scenes]
    log = [f"fixture validates: {len(plan.scenes)} scenes", f"words {words} (expected {expected}, sum {sum(words)})"]
    ok = words == expected
    return Result("PASS" if ok else "FAIL", f"words {words}", log)


def d2(skip_slow: bool) -> Result:
    code, out = _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_orchestrator.py",
                      "tests/test_numeric_guard.py", "-k", "think or format or ladder or fallback or retry or qualitative"
                      " or escalat"])
    log = ["unit: think=False / schema format / retry -> ladder -> fallback", out.strip().splitlines()[-1]]
    if code != 0:
        return Result("FAIL", "ladder unit tests fail", log + [out])
    if skip_slow:
        return Result("FAIL", "20-topic live run skipped (--skip-slow)", log)
    code, out = _run([sys.executable, "-m", "orchestrator.bench", "--stress"], timeout=7200)
    log += [out]
    m = re.search(r"valid (\d+)/(\d+) .*?final-plan failures (\d+).*?math ok (\d+) fixed (\d+).*?unspoken answers (\d+)"
                  r".*?P50 ([\d.]+)", out, re.S)
    if not m:
        return Result("FAIL", "bench output not parsed", log)
    valid, n, final_fail, _, _, unspoken, p50 = int(m[1]), int(m[2]), int(m[3]), m[4], m[5], int(m[6]), float(m[7])
    ok = valid >= 19 and p50 < 20 and final_fail == 0 and unspoken == 0
    return Result("PASS" if ok else "FAIL", f"valid {valid}/{n}, P50 {p50:.1f}s, final failures {final_fail}, "
                  f"unspoken answers {unspoken}", log)


def d3() -> Result:
    code, out = _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/", "-k",
                      "cache_hit or artifact_cache"])
    log = [out]
    tier2 = "artifact_cache" in out or (ROOT / "orchestrator" / "pipeline.py").read_text(encoding="utf-8").count(
        "def generate_lesson")
    if not tier2:
        return Result("MISSING", "tier-2 artifact cache (generate_lesson) not built", log)
    return Result("PASS" if code == 0 else "FAIL", out.strip().splitlines()[-1], log)


def _module_check(name: str, paths: list[str], test_k: str) -> Result:
    missing = [p for p in paths if not (ROOT / p).exists()]
    if missing:
        return Result("MISSING", f"not in repo: {', '.join(missing)}", [f"missing: {missing}"])
    code, out = _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/", "-k", test_k])
    last = out.strip().splitlines()[-1] if out.strip() else ""
    if "skipped" in last and "passed" not in last:
        return Result("BLOCKED", f"{name} tests all skipped: {last}", [out])
    return Result("PASS" if code == 0 else "FAIL", last, [out])


def d4() -> Result:
    return _module_check("translation", ["localization/translator.py"], "d4_")


def d5() -> Result:
    return _module_check("tts", ["localization/tts_engine.py"], "d5_")


def d6() -> Result:
    res = _module_check("renderer", ["renderer/player.html", "renderer/engine.js", "renderer/templates.js"], "d6_")
    if res.state == "MISSING":
        return res
    bad = []
    for js in (ROOT / "renderer").glob("*.js"):
        text = js.read_text(encoding="utf-8")
        for pat in ("setInterval", "Math.random", "Date.now"):
            if pat in text:
                bad.append(f"{js.name}: {pat}")
    res.log.append(f"grep setInterval / Math.random / Date.now: {bad or 'none'}")
    if bad:
        return Result("FAIL", f"non-deterministic calls: {bad}", res.log)
    return res


def d7(skip_slow: bool) -> Result:
    res = _module_check("export", ["exporter/export_mp4.py", "exporter/test_harness.py"], "d7_")
    if res.state != "PASS":
        return res
    if skip_slow:
        return Result("FAIL", "20x3 export run skipped (--skip-slow)", res.log)
    code, out = _run([sys.executable, "-m", "exporter.test_harness", "--langs", "en", "hi", "kn"], timeout=4 * 3600)
    return Result("PASS" if code == 0 else "FAIL", out.strip().splitlines()[-1] if out.strip() else "", res.log + [out])


def d8() -> Result:
    return _module_check("ui", ["exporter/app.py", "web/index.html", "web/app.js"], "d8_")


def d9() -> Result:
    if not (ROOT / "tests" / "test_e2e_offline.py").exists():
        code, out = _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/"])
        return Result("MISSING", "tests/test_e2e_offline.py not in repo; rest: " + out.strip().splitlines()[-1], [out])
    code, out = _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/"])
    return Result("PASS" if code == 0 else "FAIL", out.strip().splitlines()[-1], [out])


def d10() -> Result:
    log, problems = [], []
    readme = ROOT / "README.md"
    if not readme.exists():
        problems.append("README.md missing")
    else:
        text = readme.read_text(encoding="utf-8")
        for needle in ("License", "indictrans2", "Kokoro-82M", "mms-tts", "Noto Sans", "FFmpeg"):
            if needle.lower() not in text.lower():
                problems.append(f"README licenses table lacks {needle}")
    demo = ROOT / "run_demo.sh"
    if not demo.exists():
        problems.append("run_demo.sh missing")
    else:
        text = demo.read_text(encoding="utf-8")
        for needle in ("HF_HUB_OFFLINE=1", "TRANSFORMERS_OFFLINE=1", "OLLAMA_MAX_LOADED_MODELS=1", "warm"):
            if needle not in text:
                problems.append(f"run_demo.sh lacks {needle}")
    cached = sorted(p.name for p in (ROOT / "cache" / "artifacts").glob("*_*") if (p / "lesson.mp4").exists())
    topics = {name.rsplit("_", 1)[0] for name in cached}
    log.append(f"pre-cached artifact dirs with lesson.mp4: {len(cached)} ({len(topics)} topics)")
    if len(topics) < 10:
        problems.append(f"only {len(topics)} demo topics pre-cached (need 10)")
    log += problems
    if not readme.exists() and not demo.exists():
        return Result("MISSING", "; ".join(problems), log)
    return Result("PASS" if not problems else "FAIL", "; ".join(problems) or "ok", log)


CHECKS = {"D1": d1, "D2": d2, "D3": d3, "D4": d4, "D5": d5, "D6": d6, "D7": d7, "D8": d8, "D9": d9, "D10": d10}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", default=list(CHECKS))
    ap.add_argument("--skip-slow", action="store_true")
    args = ap.parse_args()
    LOGS.mkdir(exist_ok=True)
    rows = []
    for d in args.ids:
        t0 = time.perf_counter()
        fn = CHECKS[d]
        try:
            res = fn(args.skip_slow) if d in ("D2", "D7") else fn()
        except Exception as exc:  # a crashing check is a failing check, with the traceback as evidence
            import traceback
            res = Result("FAIL", f"{type(exc).__name__}: {exc}", [traceback.format_exc()])
        sec = time.perf_counter() - t0
        (LOGS / f"{d}.log").write_text(f"{d} {TITLES[d]} :: {res.state} :: {res.detail} ({sec:.1f}s)\n\n"
                                       + "\n".join(res.log) + "\n", encoding="utf-8")
        rows.append((d, res.state, OWNERS[d], res.detail, f"logs/{d}.log"))
        print(f"{d:<4} {res.state:<8} {res.detail}")
    table = ["| D# | check | state | owner | detail | evidence |", "|---|---|---|---|---|---|"]
    table += [f"| {d} | {TITLES[d]} | {s} | {o} | {det.replace('|', '/')} | {ev} |" for d, s, o, det, ev in rows]
    stamp = time.strftime("%Y-%m-%d %H:%M")
    (LOGS / "summary.md").write_text(f"# DONE checks · {stamp}\n\n" + "\n".join(table) + "\n", encoding="utf-8")
    return 0 if all(r[1] == "PASS" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
