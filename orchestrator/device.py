# orchestrator/device.py — one place that decides where torch models (Kokoro, IndicTrans2, MMS-TTS) run.
# Default cpu: qwen2.5:7b needs the whole RTX 3050 (5.2 GB) and already spills ~18% to CPU on its own.
import os


def get_device() -> str:
    """DEVICE=cpu|cuda (default cpu: the GPU is reserved for the qwen2.5:7b planner). cuda falls back to cpu if unavailable."""
    wanted = os.environ.get("DEVICE", "cpu").strip().lower()
    if wanted not in ("cuda", "cpu"):
        raise ValueError(f"DEVICE must be 'cuda' or 'cpu', got {wanted!r}")
    if wanted == "cpu":
        return "cpu"
    try:
        import torch
    except ImportError:
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"
