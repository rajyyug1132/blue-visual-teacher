"""Pre-generate the demo topics in every available language so the first clicks are instant (tier-2 cache).

    python scripts/precache.py                 # the 10 example topics x available languages
    python scripts/precache.py --langs en hi   # subset
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from exporter.app import EXAMPLES  # noqa: E402
from orchestrator import pipeline  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--langs", nargs="+")
    ap.add_argument("--topics", nargs="+", default=EXAMPLES)
    args = ap.parse_args()
    pipeline.warmup()
    langs = args.langs or pipeline.available_languages()
    failed = 0
    for topic in args.topics:
        for lang in langs:
            t0 = time.perf_counter()
            try:
                out = pipeline.generate_lesson(topic, lang)
                print(f"OK   {topic:<22} {lang} {time.perf_counter() - t0:6.1f}s -> {out}", flush=True)
            except Exception as exc:
                failed += 1
                print(f"FAIL {topic:<22} {lang} {type(exc).__name__}: {exc}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
