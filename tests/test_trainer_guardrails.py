"""u11 — Trainer guardrails + metrics parsing (no LLM)."""

import json

import pytest

from automl_team.stages import (MAX_EXECUTIONS, MIN_EXECUTIONS, parse_metrics_line)


def test_parse_metrics_line_good():
    stdout = (
        "loaded (1234, 106)\n"
        'METRICS_JSON: {"params": {"max_depth": 4}, "metrics": {"rmse": 14321.5, "r2": 0.61}}\n'
    )
    parsed = parse_metrics_line(stdout)
    assert parsed == {"params": {"max_depth": 4}, "metrics": {"rmse": 14321.5, "r2": 0.61}}


def test_parse_metrics_line_last_marker_wins():
    stdout = (
        'METRICS_JSON: {"params": {"a": 1}, "metrics": {"m": 1}}\n'
        "retraining…\n"
        'METRICS_JSON: {"params": {"a": 2}, "metrics": {"m": 2}}\n'
    )
    assert parse_metrics_line(stdout)["params"] == {"a": 2}


def test_parse_metrics_line_missing_or_garbled():
    assert parse_metrics_line("no marker here") is None
    assert parse_metrics_line("METRICS_JSON: {broken json}") is None
    assert parse_metrics_line('METRICS_JSON: ["not", "a", "dict"]') is None


def test_parse_metrics_line_partial_keys_default_empty():
    parsed = parse_metrics_line('METRICS_JSON: {"metrics": {"auc": 0.9}}')
    assert parsed == {"params": {}, "metrics": {"auc": 0.9}}


def test_guardrail_constants_match_spec():
    assert (MIN_EXECUTIONS, MAX_EXECUTIONS) == (2, 6)


@pytest.fixture()
def trainer_harness(tmp_path, monkeypatch):
    """Build trainer_stage's inner execute/finish_guard against a stubbed agent."""
    import pandas as pd
    from automl_team import stages
    from automl_team.events import EventLog
    from automl_team.handoff import Handoff
    from automl_team.orchestrator import StageContext

    csv = tmp_path / "02_engineered_data.csv"
    pd.DataFrame({"x": [1, 2, 3], "y": [1, 2, 3]}).to_csv(csv, index=False)
    ctx = StageContext(run_dir=tmp_path, log=EventLog(tmp_path / "events.jsonl"),
                       data_csv=csv, upstream=Handoff(csv_path=csv, report_markdown="r"))

    captured = {}

    def fake_run_agent(*, tools, finish_guard, **kwargs):
        captured["execute"] = tools[0].fn
        captured["finish_guard"] = finish_guard
        from automl_team.agent import AgentResult
        return AgentResult(finished=True, report_markdown="# done", turns=1)

    monkeypatch.setattr(stages, "run_agent", fake_run_agent)
    stages.trainer_stage(ctx)
    return captured, tmp_path


def test_finish_guard_thresholds(trainer_harness):
    captured, tmp_path = trainer_harness
    execute, guard = captured["execute"], captured["finish_guard"]
    assert "at least 2 executions" in guard("report")          # 0 runs -> reject
    execute("print('one')")
    assert "executed code 1 time" in guard("report")           # 1 run -> reject
    execute("print('two')")
    assert guard("report") is None                             # 2 runs -> accept


def test_budget_exhaustion_refuses_seventh(trainer_harness):
    captured, tmp_path = trainer_harness
    execute = captured["execute"]
    for i in range(MAX_EXECUTIONS):
        result = execute(f"print({i})")
        assert f"executions used: {i + 1}/{MAX_EXECUTIONS}" in result
    seventh = execute("print('nope')")
    assert "budget exhausted" in seventh and "finish" in seventh
    assert not (tmp_path / f"code_iter_{MAX_EXECUTIONS + 1}.py").exists()  # never ran


def test_history_file_appends_from_stdout(trainer_harness):
    captured, tmp_path = trainer_harness
    execute = captured["execute"]
    execute('print(\'METRICS_JSON: {"params": {"d": 3}, "metrics": {"rmse": 9.5}}\')')
    execute("print('forgot the marker')")
    history = json.loads((tmp_path / "03_metrics_history.json").read_text())
    assert len(history) == 1
    assert history[0]["iteration"] == 1
    assert history[0]["metrics"] == {"rmse": 9.5}


def test_missing_marker_noted_in_result(trainer_harness):
    captured, _ = trainer_harness
    result = captured["execute"]("print('just text')")
    assert "no parseable METRICS_JSON" in result
