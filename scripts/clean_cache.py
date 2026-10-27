#!/usr/bin/env python3
"""Cleans generated artifacts and plan caches safely without deleting source fixtures."""

import sys
import shutil
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clean_cache")

def clean_cache(preserve_golden: bool = True):
    cache_dir = REPO_ROOT / "cache"
    if not cache_dir.exists():
        logger.info("No cache directory found. Nothing to clean.")
        return

    artifacts_dir = cache_dir / "artifacts"
    plans_dir = cache_dir / "plans"

    cleaned_artifacts = 0
    if artifacts_dir.exists():
        for d in artifacts_dir.iterdir():
            if d.is_dir():
                if preserve_golden and "golden" in d.name.lower():
                    logger.info(f"Preserving golden artifact: {d.name}")
                    continue
                shutil.rmtree(d, ignore_errors=True)
                cleaned_artifacts += 1
        logger.info(f"Cleaned {cleaned_artifacts} artifact directories from {artifacts_dir}")

    cleaned_plans = 0
    if plans_dir.exists():
        for f in plans_dir.glob("*.json"):
            if preserve_golden and "golden" in f.name.lower():
                logger.info(f"Preserving golden plan: {f.name}")
                continue
            f.unlink()
            cleaned_plans += 1
        logger.info(f"Cleaned {cleaned_plans} cached plans from {plans_dir}")

    logger.info("Cache clean complete.")

if __name__ == "__main__":
    clean_cache()
