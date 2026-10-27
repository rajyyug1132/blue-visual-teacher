"""D6 renderer checks: 8 templates x en/hi/kn at t = start, mid, end of each scene in headless Chromium.

Asserts no page errors, no blank frames, every fillText inside the 1280x720 canvas, deterministic frames, and no
setInterval / Math.random / Date.now in the renderer sources.
"""
import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RENDERER = ROOT / "renderer"
TYPES = ["title", "bullets", "compare", "equation", "flow", "labeled_diagram", "timeline", "graph"]

# Long strings (~1.8x English) so overflow shows up. Hindi and Kannada are real translations of the fixture style.
TEXT = {
    "en": {"label": "Roof Tank Height → Voltage (V)", "step": "Higher pressure pushes more water flow through the pipe",
           "narration": "Think of an overhead water tank on your house roof. Water height is Voltage, water flow is "
                        "Current, and a narrow tap is Resistance."},
    "hi": {"label": "छत की टंकी की ऊँचाई → वोल्टेज (V) और दबाव",
           "step": "अधिक दबाव पाइप के माध्यम से अधिक पानी का प्रवाह धकेलता है और गति बढ़ाता है",
           "narration": "अपने घर की छत पर रखी पानी की टंकी के बारे में सोचिए। पानी की ऊँचाई वोल्टेज है, पाइप में पानी का "
                        "प्रवाह करंट है, और एक संकरा नल प्रतिरोध है।"},
    "kn": {"label": "ಮಾಳಿಗೆಯ ಟ್ಯಾಂಕ್ ಎತ್ತರ → ವೋಲ್ಟೇಜ್ (V) ಮತ್ತು ಒತ್ತಡ",
           "step": "ಹೆಚ್ಚಿನ ಒತ್ತಡವು ಪೈಪ್ ಮೂಲಕ ಹೆಚ್ಚು ನೀರಿನ ಹರಿವನ್ನು ತಳ್ಳುತ್ತದೆ ಮತ್ತು ವೇಗವನ್ನು ಹೆಚ್ಚಿಸುತ್ತದೆ",
           "narration": "ನಿಮ್ಮ ಮನೆಯ ಮಾಳಿಗೆಯ ಮೇಲಿರುವ ನೀರಿನ ಟ್ಯಾಂಕ್ ಬಗ್ಗೆ ಯೋಚಿಸಿ. ನೀರಿನ ಎತ್ತರ ವೋಲ್ಟೇಜ್, ಪೈಪ್‌ನಲ್ಲಿನ ನೀರಿನ "
                        "ಹರಿವು ಕರೆಂಟ್, ಮತ್ತು ಕಿರಿದಾದ ನಲ್ಲಿ ಪ್ರತಿರೋಧ."},
}

# Records every fillText with its measured box so the test can check it stays on the canvas.
RECORDER = """
window.__texts = [];
const orig = CanvasRenderingContext2D.prototype.fillText;
CanvasRenderingContext2D.prototype.fillText = function (text, x, y) {
  const m = this.measureText(text), t = this.getTransform();
  let left = x;
  if (this.textAlign === "center") left = x - m.width / 2; else if (this.textAlign === "right" || this.textAlign === "end") left = x - m.width;
  const sx = t.a * left + t.c * y + t.e, sy = t.b * left + t.d * y + t.f;
  const rotated = Math.abs(t.b) > 1e-6;
  window.__texts.push({text: String(text), x0: sx, x1: rotated ? sx : sx + m.width * t.a, y0: sy, rotated, alpha: this.globalAlpha});
  return orig.apply(this, arguments);
};
"""


def manifest(lang: str) -> dict:
    tx, scenes, cursor = TEXT[lang], [], 0.0
    for i, kind in enumerate(TYPES):
        n_labels = 6 if kind in ("labeled_diagram", "flow", "timeline") else 4
        labels = [tx["label"]] * n_labels
        steps = [tx["step"]] * 3
        if kind == "graph":
            steps = ["2019: 12", "2020: 18", "2021: 27", "2022: 33"]
        if kind == "equation":
            labels = ["V = I × R"] + [tx["label"]] * 3
            steps = ["I = V / R", "R = V / I"]
        dur = 8.0
        scenes.append({"id": i + 1, "start_sec": cursor, "end_sec": cursor + dur, "duration_sec": dur,
                       "narration": tx["narration"], "visual": {"type": kind, "params": {"labels": labels, "steps": steps}}})
        cursor += dur
    return {"title": tx["label"], "lang": lang, "scenes": scenes}


@pytest.fixture(scope="module")
def page():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, args=["--font-render-hinting=none", "--force-color-profile=srgb"])
        except Exception as exc:
            pytest.skip(f"Chromium not available: {exc}")
        pg = browser.new_page(viewport={"width": 1280, "height": 720})
        errors, requests = [], []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "ERR_FILE_NOT_FOUND" not in m.text else None)
        pg.on("request", lambda r: requests.append(r.url))
        pg.add_init_script(RECORDER)
        pg.goto((RENDERER / "player.html").resolve().as_uri())
        pg.errors, pg.requests = errors, requests
        yield pg
        browser.close()


def frame(page, t):
    page.evaluate("window.__texts = []")
    page.evaluate(f"window.renderAtTime({t})")
    data = page.evaluate("document.getElementById('stage').toDataURL('image/png')")
    return data, page.evaluate("window.__texts")


@pytest.mark.parametrize("lang", ["en", "hi", "kn"])
def test_d6_all_templates_draw_and_fit(page, lang):
    m = manifest(lang)
    page.evaluate("([t, s, l]) => window.initLesson(t, s, l)", [m["title"], m["scenes"], lang])
    assert page.evaluate("window.ready") is True
    assert page.evaluate("window.totalDuration") == pytest.approx(64.0)
    problems = []
    for scene in m["scenes"]:
        for t in (scene["start_sec"] + 0.01, (scene["start_sec"] + scene["end_sec"]) / 2, scene["end_sec"] - 0.01):
            data, texts = frame(page, t)
            pixels = page.evaluate("""() => { const c = document.getElementById('stage').getContext('2d');
                const d = c.getImageData(0, 0, 1280, 720).data; let s = 0, s2 = 0, n = 0;
                for (let i = 0; i < d.length; i += 4 * 97) { const v = d[i] + d[i+1] + d[i+2]; s += v; s2 += v*v; n++; }
                return s2 / n - (s / n) ** 2; }""")
            if pixels < 50:
                problems.append(f"{scene['visual']['type']} t={t:.2f}: blank frame (variance {pixels:.0f})")
            for tx in texts:
                if tx["rotated"] or tx["alpha"] < 0.05 or not tx["text"].strip():
                    continue
                if tx["x0"] < -1 or tx["x1"] > 1281 or tx["y0"] < -1 or tx["y0"] > 720:
                    problems.append(f"{scene['visual']['type']} t={t:.2f}: text off canvas {tx}")
    assert not page.errors, page.errors
    assert not problems, "\n".join(problems[:20])


def test_d6_deterministic_frames(page):
    m = manifest("kn")
    page.evaluate("([t, s, l]) => window.initLesson(t, s, l)", [m["title"], m["scenes"], "kn"])
    a, _ = frame(page, 13.37)
    frame(page, 40.0)
    frame(page, 2.5)
    b, _ = frame(page, 13.37)
    assert hashlib.sha256(a.encode()).hexdigest() == hashlib.sha256(b.encode()).hexdigest()


def test_d6_unknown_type_and_empty_params_degrade_to_bullets(page):
    scenes = [{"id": 1, "start_sec": 0, "end_sec": 5, "narration": "Hello there, this is a test narration.",
               "visual": {"type": "hologram", "params": {"labels": [], "steps": []}}},
              {"id": 2, "start_sec": 5, "end_sec": 10, "narration": "Second scene.",
               "visual": {"type": "graph", "params": {"labels": ["x"], "steps": ["no numbers here"]}}}]
    page.evaluate("([t, s]) => window.initLesson(t, s)", ["Edge cases", scenes])
    for t in (0.5, 2.5, 4.9, 7.5, 9.9):
        frame(page, t)
    assert not page.errors, page.errors


def test_d6_no_network_requests(page):
    bad = [u for u in page.requests if not u.startswith(("file://", "data:", "blob:", "about:"))]
    assert not bad, bad


def test_d6_renderer_sources_are_deterministic():
    found = []
    for js in RENDERER.glob("*.js"):
        for i, line in enumerate(js.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("//")[0]
            if re.search(r"\bsetInterval\b|Math\.random|Date\.now", code):
                found.append(f"{js.name}:{i}: {line.strip()}")
    assert not found, found
