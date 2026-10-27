# orchestrator/pipeline.py — checks that need real TTS output, the last layer after schema validation.
DURATION_MIN_SEC, DURATION_MAX_SEC = 30.0, 90.0


class DurationGateError(RuntimeError):
    """Measured lesson audio is outside the 30-90 s window; do not render it."""


def duration_gate(timing_manifest: list[dict]) -> float:
    """Post-TTS gate: return the measured total seconds, or raise before any frames are rendered.

    The schema only estimates duration from word counts; this checks the real audio length, which differs
    by language (Hindi and Kannada narrations run longer than the English plan).
    """
    if not timing_manifest:
        raise DurationGateError("TTS returned no scenes")
    total = timing_manifest[-1]["end_sec"]
    if not DURATION_MIN_SEC <= total <= DURATION_MAX_SEC:
        raise DurationGateError(
            f"lesson audio is {total:.2f}s, outside {DURATION_MIN_SEC:.0f}-{DURATION_MAX_SEC:.0f}s "
            f"({len(timing_manifest)} scenes)"
        )
    return total
