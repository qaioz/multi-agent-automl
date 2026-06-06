"""u15 — live-mode test: the UI reflects a growing events.jsonl (no LLM).

The 0.5s tick is streamlit's documented `run_every` behaviour; what we prove
is that the live code path re-renders appended bytes — a simulated tick is an
AppTest re-run.
"""

import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from automl_team import events as ev
from automl_team.events import EventLog

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT / "runs" / "ui-live-test"


@pytest.fixture()
def live_run_dir():
    if LIVE_DIR.exists():
        shutil.rmtree(LIVE_DIR)
    LIVE_DIR.mkdir(parents=True)
    log = EventLog(LIVE_DIR / "events.jsonl")
    log.emit("orchestrator", ev.RUN_META,
             data="x.csv", stages=["cleaner", "feature_engineer"],
             fingerprint={"rows": 3, "cols": 2, "columns": []})
    log.emit("orchestrator", ev.STAGE_START, stage="cleaner")
    log.emit("cleaner", ev.REASONING, text="first look at the data")
    yield log
    shutil.rmtree(LIVE_DIR)


def _open_live(at_path: str) -> AppTest:
    at = AppTest.from_file(at_path, default_timeout=60)
    at.run()
    at.sidebar.selectbox[0].select(str(LIVE_DIR.relative_to(ROOT))).run()
    at.sidebar.radio[0].set_value("Live (tail)").run()
    assert not at.exception, at.exception
    return at


def test_live_mode_reflects_growing_log(live_run_dir):
    at = _open_live(str(ROOT / "ui.py"))
    bubbles_before = len(at.chat_message)
    markdown_before = "".join(m.value for m in at.markdown)
    assert bubbles_before == 1
    assert "⚙️ cleaner" in markdown_before  # stepper shows cleaner running

    # the pipeline writes more events while the UI is up
    live_run_dir.emit("cleaner", ev.TOOL_CALL, tool="inspect_metadata", args={})
    live_run_dir.emit("cleaner", ev.TOOL_RESULT, tool="inspect_metadata", result="{}")
    live_run_dir.emit("cleaner", ev.REASONING, text="dropping junk rows now")
    live_run_dir.emit("orchestrator", ev.STAGE_END, stage="cleaner", status="ok")
    live_run_dir.emit("orchestrator", ev.STAGE_START, stage="feature_engineer")

    at.run()  # one simulated run_every tick
    assert not at.exception, at.exception
    assert len(at.chat_message) == 2  # transcript grew
    markdown_after = "".join(m.value for m in at.markdown)
    assert "✅ cleaner" in markdown_after          # stage flipped to done
    assert "⚙️ feature engineer" in markdown_after  # next stage running


def test_live_mode_has_no_agent_influencing_controls(live_run_dir):
    at = _open_live(str(ROOT / "ui.py"))
    # read-only window: no buttons, no inputs, no sliders anywhere
    assert not at.button
    assert not at.text_input
    assert not at.text_area
    assert not at.slider
    # the only widgets are the run picker and the mode radio
    assert len(at.sidebar.selectbox) == 1 and len(at.sidebar.radio) == 1
