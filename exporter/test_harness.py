"""Stress harness (AYUSH_BLUEPRINT 6 / BLUEPRINT 6.2): real pipeline, 20 topics x languages.

    python -m exporter.test_harness                       # 20 topics x en hi kn
    python -m exporter.test_harness --langs en --topics "Ohm's Law"

Per (topic, lang): total_sec in [30, 90]; MP4 > 150 KB; ffprobe h264 + yuv420p + aac; duration within +/-0.2 s of
the manifest; KN narration in the Kannada block with zero Devanagari; HI narration in Devanagari.
Writes reports/stress_<time>.csv and reports/frames/{slug}_{lang}_{50|last}.png; exit code 1 if any pair fails.
"""
import argparse
import csv
import json
import statistics
import subprocess
import sys
import time
import traceback
from pathlib import Path

from exporter.export_mp4 import probe
from orchestrator import pipeline
from orchestrator.bench import STRESS_TOPICS

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"


def script_ok(lang: str, text: str) -> str:
    kn = sum("ಀ" <= c <= "೿" for c in text)
    dev = sum("ऀ" <= c <= "ॿ" for c in text)
    if lang == "kn" and (kn == 0 or dev > 0):
        return f"kannada chars {kn}, devanagari chars {dev}"
    if lang == "hi" and dev == 0:
        return "no devanagari in hindi narration"
    return ""


def save_frames(mp4: Path, total: float, stem: str) -> None:
    frames = REPORTS / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for tag, t in (("50", total / 2), ("last", max(0.0, total - 0.1))):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(mp4), "-frames:v", "1",
                        str(frames / f"{stem}_{tag}.png")], check=False)


def check_pair(topic: str, lang: str) -> dict:
    row = {"topic": topic, "lang": lang, "ok": False, "notes": ""}
    t0 = time.perf_counter()
    try:
        out = pipeline.generate_lesson(topic, lang)
    except Exception as exc:
        row["notes"] = f"{type(exc).__name__}: {exc}"[:300]
        traceback.print_exc()
        return row
    row["total_gen_s"] = round(time.perf_counter() - t0, 1)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    tel = json.loads((out / "telemetry.json").read_text(encoding="utf-8")) if (out / "telemetry.json").exists() else {}
    for k, v in tel.get("stage_sec", {}).items():
        row[f"{k}_s"] = v
    planner = tel.get("planner", {})
    row["fallback"] = planner.get("fallback_used")
    total = float(manifest["total_sec"])
    info = probe(out / "lesson.mp4")
    row.update(total_sec=round(total, 2), mp4_kb=round(info["kb"]), mp4_sec=round(info["duration"], 2))
    problems = []
    if not 30.0 <= total <= 90.0:
        problems.append(f"total {total:.1f}s outside 30-90")
    if info["kb"] <= 150:
        problems.append(f"mp4 {info['kb']:.0f} KB")
    if (info["video"], info["pix_fmt"], info["audio"]) != ("h264", "yuv420p", "aac"):
        problems.append(f"streams {info['video']}/{info['pix_fmt']}/{info['audio']}")
    if abs(info["duration"] - total) > 0.2:
        problems.append(f"duration {info['duration']:.2f} vs manifest {total:.2f}")
    if (msg := script_ok(lang, " ".join(s["narration"] for s in manifest["scenes"]))):
        problems.append(msg)
    save_frames(out / "lesson.mp4", total, out.name)
    row["ok"] = not problems
    row["notes"] = "; ".join(problems)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--langs", nargs="+", default=["en", "hi", "kn"])
    ap.add_argument("--topics", nargs="+", default=STRESS_TOPICS)
    args = ap.parse_args()
    REPORTS.mkdir(exist_ok=True)
    pipeline.warmup()
    rows = []
    for topic in args.topics:
        for lang in args.langs:
            row = check_pair(topic, lang)
            rows.append(row)
            print(f"{'PASS' if row['ok'] else 'FAIL'} {topic[:28]:<28} {lang} {row.get('total_sec', '-'):>6}s "
                  f"gen {row.get('total_gen_s', '-')}s {row['notes']}", flush=True)
    path = REPORTS / f"stress_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    fields = sorted({k for r in rows for k in r}, key=lambda k: (k not in ("topic", "lang", "ok", "notes"), k))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    for lang in args.langs:
        gens = [r["total_gen_s"] for r in rows if r["lang"] == lang and "total_gen_s" in r]
        if gens:
            print(f"{lang}: P50 {statistics.median(gens):.1f}s P90 {sorted(gens)[max(0, int(len(gens) * 0.9) - 1)]:.1f}s")
    passed = sum(r["ok"] for r in rows)
    fallbacks = sum(bool(r.get("fallback")) for r in rows if r["lang"] == args.langs[0])
    print(f"harness: {passed}/{len(rows)} pass · fallback topics {fallbacks}/{len(args.topics)} · report {path}")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
