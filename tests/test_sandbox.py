"""u10 — sandbox tests: ok / crash / timeout, verbatim events, run-dir cwd (no LLM)."""

from pathlib import Path

import pytest

from automl_team import events as ev
from automl_team.events import EventLog, read_events
from automl_team.tools.sandbox import Sandbox


@pytest.fixture()
def sandbox(tmp_path):
    return Sandbox(tmp_path, EventLog(tmp_path / "events.jsonl"), timeout=5)


def events_of(sandbox) -> list[dict]:
    return read_events(sandbox.run_dir / "events.jsonl")


def test_ok_code_verbatim_stdout(sandbox):
    result = sandbox.execute_python_code("print('metric: 0.8731')\nprint(6 * 7)")
    assert "returncode: 0" in result
    assert "metric: 0.8731" in result and "42" in result
    event = events_of(sandbox)[-1]
    assert event["type"] == ev.EXECUTION
    assert event["payload"]["stdout"] == "metric: 0.8731\n42\n"  # verbatim
    assert event["payload"]["returncode"] == 0
    assert event["payload"]["iteration"] == 1


def test_crash_verbatim_traceback(sandbox):
    result = sandbox.execute_python_code("raise ValueError('bad feature dtype')")
    assert "returncode: 1" in result
    assert "ValueError: bad feature dtype" in result
    assert "Traceback" in result
    event = events_of(sandbox)[-1]
    assert "ValueError: bad feature dtype" in event["payload"]["stderr"]


def test_timeout_returned_as_stderr(sandbox):
    result = sandbox.execute_python_code(
        "import time\nprint('started', flush=True)\ntime.sleep(60)"
    )
    assert "returncode: -1" in result
    assert "TimeoutError: execution exceeded the 5s limit" in result
    event = events_of(sandbox)[-1]
    assert "exceeded the 5s limit" in event["payload"]["stderr"]
    assert event["payload"]["returncode"] == -1


def test_code_files_saved_and_counter(sandbox):
    sandbox.execute_python_code("print(1)")
    sandbox.execute_python_code("print(2)")
    assert sandbox.executions == 2
    assert (sandbox.run_dir / "code_iter_1.py").read_text() == "print(1)"
    assert (sandbox.run_dir / "code_iter_2.py").read_text() == "print(2)"
    assert [e["payload"]["iteration"] for e in events_of(sandbox)] == [1, 2]


def test_cwd_is_run_dir(sandbox):
    sandbox.execute_python_code(
        "from pathlib import Path\n"
        "Path('artifact.txt').write_text('here')\n"
        "print(Path.cwd())"
    )
    assert (sandbox.run_dir / "artifact.txt").read_text() == "here"


def test_project_venv_packages_available(sandbox):
    result = sandbox.execute_python_code(
        "import pandas, xgboost, sklearn\nprint('imports ok')"
    )
    assert "returncode: 0" in result and "imports ok" in result


def test_truncation_for_agent_but_verbatim_event(sandbox):
    result = sandbox.execute_python_code("print('x' * 20000)")
    assert "chars omitted — full output is in the log" in result
    assert len(result) < 10000
    event = events_of(sandbox)[-1]
    assert len(event["payload"]["stdout"]) >= 20000  # event keeps every byte
