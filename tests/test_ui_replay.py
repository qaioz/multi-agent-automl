"""u14 — replay UI smoke test via streamlit AppTest (headless, no API key)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent


def local_runs_exist() -> bool:
    for root in (ROOT / "runs", ROOT / "examples"):
        if root.exists() and any((d / "events.jsonl").exists() for d in root.iterdir()):
            return True
    return False


@pytest.mark.skipif(not local_runs_exist(), reason="no local run dir to replay")
def test_replay_renders_without_exception_and_without_key(monkeypatch):
    # replay must not need an API key — prove it by removing it
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    at = AppTest.from_file(str(ROOT / "ui.py"), default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    assert at.title and "Multi-Agent AutoML Team" in at.title[0].value
    assert at.sidebar.selectbox, "run picker missing"
    assert len(at.sidebar.selectbox[0].options) >= 1
    assert at.tabs, "main tab bar missing"


@pytest.mark.skipif(not local_runs_exist(), reason="no local run dir to replay")
def test_replay_switching_runs_keeps_rendering(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    at = AppTest.from_file(str(ROOT / "ui.py"), default_timeout=60)
    at.run()
    options = at.sidebar.selectbox[0].options
    if len(options) > 1:  # pick the oldest run instead of the default newest
        at.sidebar.selectbox[0].select_index(len(options) - 1).run()
        assert not at.exception, at.exception
