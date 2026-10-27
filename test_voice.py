import warnings
warnings.filterwarnings("ignore")
"""test_voice.py — Interactive Voice Testing CLI for Localization TTS Engine.

Usage:
    python test_voice.py --lang en
    python test_voice.py --lang kn --text "ಓಮ್‌ನ ನಿಯಮದ ಪ್ರಕಾರ ವೋಲ್ಟೇಜ್ ಕರೆಂಟ್‌ಗೆ ನೇರ ಅನುಪಾತದಲ್ಲಿರುತ್ತದೆ."
    python test_voice.py --lang ta --text "ஓம் விதிப்படி மின்னழுத்தம் மின்னோட்டத்திற்கு நேர்விகிதத்தில் இருக்கும்."
    python test_voice.py --lang bn --text "ওহমের সূত্র অনুসারে ভোল্টেজ কারেন্টের সমানুপাতিক।"
    python test_voice.py --lang hi --text "ओम के नियम के अनुसार वोल्टेज विद्युत धारा के समानुपाती होता है।"
    python test_voice.py --play  # Automatically plays the audio after generation
"""

import argparse
import os
import struct
import subprocess
import sys
import wave
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure local offline paths
# Automatically use the project's torch-enabled venv if run from standard python
try:
    import torch
except ImportError:
    for candidate in [
        Path(r"D:\git\project requirements\venv\Scripts\python.exe"),
        Path(r"D:\git\unlox\.venv311\Scripts\python.exe"),
    ]:
        if candidate.is_file() and str(candidate).lower() != sys.executable.lower():
            print(f"[test_voice] Switching to project ML environment ({candidate.name})...")
            res = subprocess.run([str(candidate)] + sys.argv)
            sys.exit(res.returncode)

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Sample natural textbook test sentences for each supported language
DEFAULT_TEXTS = {
    "en": "Welcome to our physics lesson on Ohm's Law. Voltage across a resistor equals current times resistance.",
    "hi": "ओम के नियम के अनुसार, एक चालक में बहने वाली विद्युत धारा उसके सिरों के विभवांतर के समानुपाती होती है।",
    "kn": "ಓಮ್‌ನ ನಿಯಮದ ಪ್ರಕಾರ, ವಾಹಕದಲ್ಲಿ ಹರಿಯುವ ವಿದ್ಯುತ್ ಪ್ರವಾಹವು ಅದರ ತುದಿಗಳ ನಡುವಿನ ವೋಲ್ಟೇಜ್‌ಗೆ ನೇರ ಅನುಪಾತದಲ್ಲಿರುತ್ತದೆ.",
    "ta": "ஓம் விதிப்படி, ஒரு கடத்தியின் வழியே பாயும் மின்னோட்டம் அதன் முனைகளுக்கு இடைப்பட்ட மின்னழுத்த வேறுபாட்டிற்கு நேர்விகிதத்தில் இருக்கும்.",
    "bn": "ওহমের সূত্র অনুসারে, একটি পরিবাহীর মধ্য দিয়ে প্রবাহিত তড়িৎ প্রবাহ তার দুই প্রান্তের বিভব পার্থক্যের সমানুপাতিক।",
}


def synthesize_and_save(lang: str, text: str, voice: str | None = None, target_dur: float | None = None, ref_text: str | None = None, play: bool = False) -> Path:
    from localization.tts_engine import OfflineTTSEngine

    print(f"\n[TTS Engine] Initializing voice synthesizer for '{lang}'...")
    kwargs = {}
    if voice and lang == "en":
        kwargs["voice_en"] = voice
    elif voice and lang == "hi":
        kwargs["voice_hi"] = voice
    tts = OfflineTTSEngine(**kwargs)

    engine_desc = "Synthetic Fallback"
    if lang == "en" and tts.kokoro_en is not None:
        engine_desc = f"Kokoro-82M (Voice: {tts.voice_en}, Speed: {tts.speed_en}x)"
    elif lang == "hi" and tts.kokoro_hi is not None:
        engine_desc = f"Kokoro-82M (Voice: {tts.voice_hi}, Speed: {tts.speed_hi}x)"
    elif lang in tts.mms_models:
        engine_desc = f"Meta MMS-TTS ({lang}) with VITS Duration Predictor"

    print(f"[Engine Model] {engine_desc}")
    print(f"[Input Text]   {text}")
    ref_ratios = None
    if ref_text:
        ref_ratios = tts.extract_segment_ratios(ref_text, "en")
        print(f"[Proportional Sync] English reference timing profile: {[round(r, 3) for r in ref_ratios]}")
    if target_dur:
        print(f"[Timing Sync]  Target duration locked to {target_dur:.3f}s (Proportional Segment Scaling)")

    wav, dur = tts.synthesize_scene(text, lang, target_dur=target_dur, ref_ratios=ref_ratios)

    suffix = f"_{target_dur:.1f}s" if target_dur else ""
    out_path = Path("cache") / f"test_voice_{lang}{suffix}.wav"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
                # 0.35s head padding prevents DAC / media player latency from swallowing the first word
        head_pad = [0] * int(0.35 * 24000)
        samples = head_pad + [max(-32768, min(32767, int(s * 32767.0))) for s in wav]
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    print(f"[Output Saved] {out_path.resolve()} ({dur:.2f}s, {len(wav)} samples @ 24,000 Hz)")

    if play:
        print("[Audio Player] Opening system media player...")
        if sys.platform == "win32":
            os.startfile(str(out_path.resolve()))
        elif sys.platform == "darwin":
            subprocess.run(["afplay", str(out_path)])
        else:
            subprocess.run(["xdg-open", str(out_path)])

    return out_path


def main():
    parser = argparse.ArgumentParser(description="Test voice generation for any supported language.")
    parser.add_argument(
        "--lang",
        default="en",
        choices=["en", "hi", "kn", "ta", "bn"],
        help="Target language code (default: 'en')",
    )
    parser.add_argument(
        "--voice",
        default=None,
        help="Custom voice ID (e.g. 'am_michael', 'af_bella', 'bm_george' for English; 'hf_alpha', 'hm_omega' for Hindi)",
    )
    parser.add_argument(
        "--text",
        default=None,
        help="Custom text to speak. If omitted, uses a standard STEM lesson sentence.",
    )
    parser.add_argument(
        "--ref-text",
        default=None,
        help="English reference text to extract clause duration proportions from.",
    )
    parser.add_argument(
        "--target-dur",

        type=float,
        default=None,
        help="Target duration in seconds to lock the speech to using time expansion/compression.",
    )
    parser.add_argument(
        "--play",
        action="store_true",
        help="Automatically open and play the generated WAV file in default media player.",
    )

    args = parser.parse_args()
    text = args.text or DEFAULT_TEXTS.get(args.lang, DEFAULT_TEXTS["en"])
    synthesize_and_save(args.lang, text, voice=args.voice, target_dur=args.target_dur, ref_text=args.ref_text, play=args.play)


if __name__ == "__main__":
    main()
