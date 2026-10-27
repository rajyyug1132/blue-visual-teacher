"""D8 web UI in headless Chromium against the real FastAPI app (stubbed models, real exporter).

Language selector EN/HI/KN, progress stepper and bar, error toast with Retry, MP4 download link that serves the file.
"""
import socket
import sys
import threading
import time
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from orchestrator import pipeline  # noqa: E402
from test_e2e_offline import WordRateTTS, golden_plan, require_exporter  # noqa: E402


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    require_exporter()
    import uvicorn
    from exporter import app as app_module

    app_module.app.state.skip_warmup = True
    app_module.state["languages"] = ["en", "hi", "kn"]
    behaviour = {"fail": False}

    def generate(topic, lang, cb):
        if behaviour["fail"]:
            cb("plan", 10)
            raise RuntimeError("model crashed with a long traceback nobody should see")
        return pipeline.generate_lesson(topic, lang, cb, tts=WordRateTTS(), plan_fn=golden_plan,
                                        translator=_Identity())

    app_module.app.state.generate = generate
    port = free_port()
    srv = uvicorn.Server(uvicorn.Config(app_module.app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    topics = []
    yield f"http://127.0.0.1:{port}", behaviour, topics
    srv.should_exit = True
    thread.join(timeout=5)
    import shutil
    for t in topics:
        for lang in ("en", "hi", "kn"):
            shutil.rmtree(pipeline.artifact_dir(t, lang), ignore_errors=True)


class _Identity:
    """Translator stand-in: keeps English text, so the UI flow can be tested without IndicTrans2."""

    def localize_lesson(self, plan, lang):
        return plan


@pytest.fixture
def page(server):
    sync_api = pytest.importorskip("playwright.sync_api")
    base, _, _ = server
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pg = browser.new_page(viewport={"width": 1366, "height": 768})
        errors, external = [], []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("request", lambda r: None if r.url.startswith((base, "data:", "blob:")) else external.append(r.url))
        pg.goto(base + "/")
        pg.wait_for_selector("#langs .chip")
        pg.errors, pg.external = errors, external
        yield pg
        browser.close()


def test_d8_language_selector_offers_en_hi_kn(page):
    chips = page.locator("#langs .chip")
    assert chips.count() == 3
    assert [chips.nth(i).get_attribute("data-lang") for i in range(3)] == ["en", "hi", "kn"]
    assert chips.nth(2).inner_text() == "ಕನ್ನಡ"
    chips.nth(1).click()
    assert chips.nth(1).get_attribute("aria-checked") == "true"


def test_d8_generate_shows_progress_then_player_and_download(page, server):
    base, behaviour, topics = server
    behaviour["fail"] = False
    topic = f"UI Flow {uuid.uuid4().hex[:6]}"
    topics.append(topic)
    page.fill("#topic", topic)
    page.click("#go")
    page.wait_for_selector("#progress:not([hidden])")
    page.wait_for_selector("#stepper li.active, #stepper li.done")
    page.wait_for_selector("#player:not([hidden])", timeout=240_000)
    assert page.evaluate("document.getElementById('bar-fill').style.width") == "100%"
    assert page.locator("#stepper li.done").count() == 5
    href = page.get_attribute("#download", "href")
    assert href.endswith("/lesson.mp4")
    resp = page.request.get(base + href)
    assert resp.status == 200 and len(resp.body()) > 150 * 1024
    assert page.evaluate("window.totalDuration") > 30
    assert not page.errors, page.errors
    assert not page.external, page.external


def test_d8_errors_show_a_friendly_toast_with_retry(page, server):
    _, behaviour, _ = server
    behaviour["fail"] = True
    try:
        page.fill("#topic", f"Broken {uuid.uuid4().hex[:6]}")
        page.click("#go")
        page.wait_for_selector("#toast:not([hidden])", timeout=30_000)
        text = page.inner_text("#toast-text")
        assert "traceback" not in text.lower() and "Please retry" in text
        assert page.is_visible("#retry")
    finally:
        behaviour["fail"] = False


def test_d8_topic_validation_is_inline(page):
    page.fill("#topic", "x")
    page.click("#go")
    assert "at least 2 characters" in page.inner_text("#hint")
    assert page.is_hidden("#progress")
