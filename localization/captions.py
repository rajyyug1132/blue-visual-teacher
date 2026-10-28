"""localization/captions.py — Word-level timing and subtitle generator.

Calculates proportional word timing across scene duration:
  start + 0.15 + frac_k * (dur - 0.5)
Weights words by character length to match natural human speech cadences.
Exports timed words, SRT, and VTT subtitle formats.
"""

from __future__ import annotations

import math
from typing import Sequence


def compute_word_timings(
    narration: str,
    scene_start_sec: float,
    scene_dur_sec: float,
    head_pad_sec: float = 0.15,
    tail_buffer_sec: float = 0.50,
) -> list[dict[str, float | str]]:
    """Compute proportional word-by-word highlight timings for a scene narration.
    
    Conforms to FARHAN_BLUEPRINT.md section 5:
      active window across [scene_start + 0.15, scene_start + dur - 0.35]
    """
    words = narration.strip().split()
    if not words:
        return []

    # Effective speech window (excluding initial pause and silent tail buffer)
    active_span = max(0.5, scene_dur_sec - head_pad_sec - (tail_buffer_sec - head_pad_sec))
    speech_start = scene_start_sec + head_pad_sec

    # Weight each word by character count + 1 for word space
    weights = [max(1, len(w)) for w in words]
    total_weight = sum(weights)

    timings: list[dict[str, float | str]] = []
    cumulative_weight = 0

    for idx, (word, w_len) in enumerate(zip(words, weights)):
        start_frac = cumulative_weight / total_weight
        end_frac = (cumulative_weight + w_len) / total_weight
        word_start = round(speech_start + (start_frac * active_span), 3)
        word_end = round(speech_start + (end_frac * active_span), 3)

        timings.append({
            "index": idx,
            "word": word,
            "start_sec": word_start,
            "end_sec": word_end,
        })
        cumulative_weight += w_len

    return timings


def generate_srt(scene_timings: Sequence[dict]) -> str:
    """Generate SubRip (.srt) subtitle text from scene timings."""
    def _format_time(sec: float) -> str:
        hrs = int(sec // 3600)
        mins = int((sec % 3600) // 60)
        secs = int(sec % 60)
        millis = int(round((sec - int(sec)) * 1000))
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    lines = []
    for i, s in enumerate(scene_timings, 1):
        lines.append(str(i))
        start_str = _format_time(s["start_sec"])
        end_str = _format_time(s["end_sec"])
        lines.append(f"{start_str} --> {end_str}")
        lines.append(s["narration"])
        lines.append("")

    return "\n".join(lines)


def generate_vtt(scene_timings: Sequence[dict]) -> str:
    """Generate WebVTT (.vtt) subtitle text from scene timings."""
    def _format_time(sec: float) -> str:
        hrs = int(sec // 3600)
        mins = int((sec % 3600) // 60)
        secs = int(sec % 60)
        millis = int(round((sec - int(sec)) * 1000))
        return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"

    lines = ["WEBVTT", ""]
    for i, s in enumerate(scene_timings, 1):
        lines.append(str(i))
        start_str = _format_time(s["start_sec"])
        end_str = _format_time(s["end_sec"])
        lines.append(f"{start_str} --> {end_str}")
        lines.append(s["narration"])
        lines.append("")

    return "\n".join(lines)
