"""localization/warmup.py — Environment readiness & model pre-caching script.

Verifies:
  1. Python version (warns if running 3.14 due to Windows C-extension wheel compatibility).
  2. External dependencies (espeak-ng on PATH for Kokoro Hindi).
  3. Pre-caches and warms up Kokoro voice packs (af_heart.pt, hf_alpha.pt) while online,
     preventing crashes when HF_HUB_OFFLINE=1 during offline demos.
  4. Pre-caches and tests MMS-TTS Kannada (facebook/mms-tts-kan) and IndicTrans2 checkpoints.
  5. Prints an OK/FAIL status table per component.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def check_python_environment() -> tuple[str, str]:
    ver = sys.version_info
    ver_str = f"{ver.major}.{ver.minor}.{ver.micro}"
    if (ver.major, ver.minor) in ((3, 11), (3, 12)):
        return "OK", f"Python {ver_str} (optimal for PyTorch/Windows wheels)"
    elif (ver.major, ver.minor) >= (3, 14):
        return (
            "WARN",
            f"Python {ver_str} detected. Note: Activate Python 3.11/3.12 (.venv) for binary wheel support.",
        )
    return "OK", f"Python {ver_str}"


def check_espeak() -> tuple[str, str]:
    has_espeak = bool(shutil.which("espeak-ng") or shutil.which("espeak"))
    if has_espeak:
        return "OK", "espeak-ng found on PATH"
    return (
        "WARN",
        "espeak-ng not found on PATH. (Required for Kokoro Hindi; MMS-TTS fallback will be used on Windows).",
    )


def warmup_kokoro() -> tuple[str, str]:
    try:
        from kokoro import KPipeline
        # English warmup
        pipe_en = KPipeline(lang_code="a")
        _ = list(pipe_en("Warmup test.", voice="af_heart"))
        # Hindi warmup (if espeak is installed)
        if shutil.which("espeak-ng") or shutil.which("espeak"):
            pipe_hi = KPipeline(lang_code="h")
            _ = list(pipe_hi("नमस्ते परीक्षण।", voice="hf_alpha"))
            return "OK", "Kokoro-82M English (af_heart) & Hindi (hf_alpha) cached"
        return "OK", "Kokoro-82M English (af_heart) cached"
    except Exception as exc:
        return "FAIL", f"Kokoro warmup failed: {exc}"


def warmup_mms_kannada() -> tuple[str, str]:
    try:
        from transformers import AutoTokenizer, VitsModel
        import torch

        repo = "facebook/mms-tts-kan"
        tokenizer = AutoTokenizer.from_pretrained(repo)
        model = VitsModel.from_pretrained(repo)
        inputs = tokenizer("ಪರೀಕ್ಷೆ", return_tensors="pt")
        torch.manual_seed(42)
        with torch.no_grad():
            _ = model(**inputs).waveform
        return "OK", "MMS-TTS Kannada (facebook/mms-tts-kan) cached and verified"
    except Exception as exc:
        return "FAIL", f"MMS-TTS Kannada warmup failed: {exc}"


def warmup_indictrans2() -> tuple[str, str]:
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        from IndicTransToolkit import IndicProcessor

        ckpt = "ai4bharat/indictrans2-en-indic-dist-200M"
        _ = IndicProcessor(inference=True)
        _ = AutoTokenizer.from_pretrained(ckpt, trust_remote_code=True)
        _ = AutoModelForSeq2SeqLM.from_pretrained(ckpt, trust_remote_code=True)
        return "OK", "IndicTrans2 200M checkpoint cached"
    except Exception as exc:
        return "FAIL", f"IndicTrans2 warmup failed: {exc}"


def run_all_warmups():
    print("\n" + "=" * 80)
    print("LOCALIZATION ENVIRONMENT & MODEL WARMUP CHECK")
    print("=" * 80)

    checks = [
        ("Python Version", check_python_environment),
        ("espeak-ng (Hindi G2P)", check_espeak),
        ("Kokoro-82M Voices", warmup_kokoro),
        ("MMS-TTS Kannada", warmup_mms_kannada),
        ("IndicTrans2 200M", warmup_indictrans2),
    ]

    for name, fn in checks:
        status, msg = fn()
        badge = f"[{status}]"
        print(f"{badge:<8} {name:<24} : {msg}")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_all_warmups()
