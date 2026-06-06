"""u03 — EventLog round-trip + console renderer tests (no LLM)."""

import json

import pytest

from automl_team import console
from automl_team import events as ev
from automl_team.events import EventLog, read_events

# One representative event per type: (agent, type, payload)
SAMPLES = [
    ("orchestrator", ev.RUN_META, {"data": "data/x.csv", "model": "gemini-2.5-flash"}),
    ("orchestrator", ev.STAGE_START, {"stage": "cleaner"}),
    ("cleaner", ev.TOOL_CALL, {"tool": "impute_missing", "args": {"column": "Сontract duration", "strategy": "mode"}}),
    ("cleaner", ev.TOOL_RESULT, {"tool": "impute_missing", "result": "filled 152 NaNs in 'Сontract duration'"}),
    ("cleaner", ev.REASONING, {"text": "70 % missing — skip-logic column, imputing would invent data"}),
    ("trainer", ev.EXECUTION, {"iteration": 1, "returncode": 1, "stdout": "", "stderr": "ValueError: could not convert"}),
    ("trainer", ev.ITERATION_METRICS, {"iteration": 2, "params": {"max_depth": 4}, "metrics": {"rmse": 14321.5}}),
    ("cleaner", ev.HANDOFF, {"csv_path": "01_clean_data.csv", "report_markdown": "# Cleaning\n…"}),
    ("orchestrator", ev.STAGE_END, {"stage": "cleaner", "status": "ok"}),
    ("orchestrator", ev.ERROR, {"message": "boom"}),
]


def test_round_trip_all_types(tmp_path):
    log_path = tmp_path / "events.jsonl"
    log = EventLog(log_path)
    emitted = [log.emit(agent, type, **payload) for agent, type, payload in SAMPLES]

    got = read_events(log_path)
    assert len(got) == len(SAMPLES)
    for event, (agent, type, payload) in zip(got, SAMPLES):
        assert event["agent"] == agent
        assert event["type"] == type
        assert event["payload"] == payload  # exact, unicode intact
        assert event["ts"].endswith("+00:00")  # UTC ISO-8601
    assert got == emitted  # emit() returns exactly what was written


def test_every_type_covered_by_samples():
    assert {t for _, t, _ in SAMPLES} == set(ev.EVENT_TYPES)


def test_unknown_type_rejected(tmp_path):
    log = EventLog(tmp_path / "events.jsonl")
    with pytest.raises(ValueError, match="unknown event type"):
        log.emit("cleaner", "thought")


def test_append_only_across_reopens(tmp_path):
    path = tmp_path / "events.jsonl"
    EventLog(path).emit("orchestrator", ev.STAGE_START, stage="a")
    EventLog(path).emit("orchestrator", ev.STAGE_END, stage="a", status="ok")
    got = read_events(path)
    assert [e["type"] for e in got] == [ev.STAGE_START, ev.STAGE_END]


def test_partial_trailing_line_tolerated(tmp_path):
    path = tmp_path / "events.jsonl"
    EventLog(path).emit("trainer", ev.REASONING, text="ok")
    with path.open("a", encoding="utf-8") as f:
        f.write('{"ts": "2026-06-06T00:00:00+00:00", "agent": "trainer", "ty')  # mid-write
    got = read_events(path)
    assert len(got) == 1  # partial line skipped, no crash


def test_read_missing_file(tmp_path):
    assert read_events(tmp_path / "nope.jsonl") == []


def test_console_renders_every_type(tmp_path):
    log = EventLog(tmp_path / "events.jsonl")
    for agent, type, payload in SAMPLES:
        line = console.render(log.emit(agent, type, **payload))
        assert line.startswith(f"[{agent}] ")
        assert len(line) > len(agent) + 5
        assert "\n" not in line  # one line per event


def test_console_key_info_present(tmp_path):
    log = EventLog(tmp_path / "e.jsonl")
    call = log.emit("cleaner", ev.TOOL_CALL, tool="drop_column", args={"column": "Position "})
    assert "drop_column" in console.render(call)
    reasoning = log.emit("cleaner", ev.REASONING, text="salary outliers above 1e8 are junk")
    assert "salary outliers" in console.render(reasoning)
    execution = log.emit("trainer", ev.EXECUTION, iteration=3, returncode=0,
                         stdout="rmse=123", stderr="")
    line = console.render(execution)
    assert "rc=0" in line and "rmse=123" in line
    long = log.emit("trainer", ev.REASONING, text="x" * 1000)
    assert len(console.render(long)) < 250  # truncated


def test_unicode_survives_bytes(tmp_path):
    """Cyrillic С must survive write→read byte-for-byte (ensure_ascii=False)."""
    path = tmp_path / "events.jsonl"
    EventLog(path).emit("cleaner", ev.TOOL_CALL, tool="get_column_stats",
                        args={"column": "Сontract duration"})
    raw = path.read_text(encoding="utf-8")
    assert "Сontract duration" in raw  # not С-escaped
    assert read_events(path)[0]["payload"]["args"]["column"][0] == "С"
