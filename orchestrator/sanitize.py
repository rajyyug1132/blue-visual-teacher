"""LLM output sanitization ('token sterilization').

Strips chat tokens, reasoning blocks, markdown decorations, stray emojis,
control characters, and small-model output prefixes before schema validation.
Never cleans params.code or trace (code walkthrough must preserve symbols).
"""
import re
import unicodedata


def _is_emoji_or_control(c: str) -> bool:
    cp = ord(c)
    cat = unicodedata.category(c)
    # Preserve Indic joiners and formatting spaces
    if c in ("\u200c", "\u200d", "\n", "\r", "\t"):
        return False
    # Drop control characters
    if cat.startswith("C"):
        return True
    # Drop emojis and dingbats in standard Unicode blocks
    if 0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF or cp in (0xFE0E, 0xFE0F):
        return True
    return False


def clean_text(s: str) -> str:
    """Normalize and clean string fields emitted by LLM planner.

    - NFKC Unicode normalization
    - Strip <think>...</think> reasoning blocks
    - Remove special tokens: <|im_start|>, <|im_end|>, <|endoftext|>, <|eot_id|>, </s>, <s>, [INST], [/INST]
    - Strip markdown: **bold**, __x__, `code`, leading '#', leading list markers ('- ', '* ', '1. ')
    - Drop emojis and control characters (preserves Indic, Latin, digits, punctuation)
    - Drop leading prefixes: 'Scene 3:', 'Narration:', 'Label:', etc.
    - Strip wrapping quotes and collapse whitespace
    - Strictly idempotent
    """
    if not isinstance(s, str) or not s:
        return s if isinstance(s, str) else ""

    # 1. NFKC normalization
    s = unicodedata.normalize("NFKC", s)

    # 2. Reasoning blocks
    s = re.sub(r"<think>.*?</think>", "", s, flags=re.DOTALL | re.IGNORECASE)

    # 3. Special tokens
    s = re.sub(r"<\|(?:im_start|im_end|endoftext|eot_id)\|>|<\/?[sS]>|\[\/?INST\]", "", s)

    # 4. Inline markdown
    s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
    s = re.sub(r"__(.*?)__", r"\1", s)
    s = re.sub(r"`(.*?)`", r"\1", s)

    # 5. Drop emojis and control characters
    s = "".join(c for c in s if not _is_emoji_or_control(c))

    # 6. Prefixes, list markers, leading '#', wrapping quotes
    for _ in range(5):
        prev = s
        s = s.strip()
        s = re.sub(r"^#+\s*", "", s)
        s = re.sub(r"^(?:[-*•]|\d+\.)\s+", "", s)
        s = re.sub(r"^(?:scene\s*\d*|narration|label|step\s*\d*|title)\s*[:\-.]\s*", "", s, flags=re.IGNORECASE)
        s = s.strip("'\"“”‘’")
        if s == prev:
            break

    # 7. Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def sanitize_plan_dict(data: dict) -> dict:
    """Clean every string field in a parsed plan dictionary except code/trace."""
    if not isinstance(data, dict):
        return data

    if isinstance(data.get("title"), str):
        data["title"] = clean_text(data["title"])

    scenes = data.get("scenes")
    if isinstance(scenes, list):
        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            if isinstance(scene.get("title"), str):
                scene["title"] = clean_text(scene["title"])
            if isinstance(scene.get("narration"), str):
                scene["narration"] = clean_text(scene["narration"])
            visual = scene.get("visual")
            if isinstance(visual, dict):
                params = visual.get("params")
                if isinstance(params, dict):
                    if isinstance(params.get("labels"), list):
                        params["labels"] = [
                            clean_text(x) if isinstance(x, str) else x for x in params["labels"]
                        ]
                    if isinstance(params.get("steps"), list):
                        params["steps"] = [
                            clean_text(x) if isinstance(x, str) else x for x in params["steps"]
                        ]
                    # code and trace are left untouched
    return data
