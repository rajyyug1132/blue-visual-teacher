# orchestrator/device.py — one place that decides where torch models (Kokoro, IndicTrans2, MMS-TTS) run.
import os


def get_device() -> str:
    """DEVICE=cuda|cpu (default cuda). Falls back to cpu when CUDA is requested but unavailable."""
    wanted = os.environ.get("DEVICE", "cuda").strip().lower()
    if wanted not in ("cuda", "cpu"):
        raise ValueError(f"DEVICE must be 'cuda' or 'cpu', got {wanted!r}")
    if wanted == "cpu":
        return "cpu"
    try:
        import torch
    except ImportError:
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"
