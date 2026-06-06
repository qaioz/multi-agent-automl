"""u04 — orchestrator skeleton tests: dummy stages, no LLM."""

import pandas as pd
import pytest

from automl_team import events as ev
from automl_team.events import read_events
from automl_team.handoff import Handoff
from automl_team.orchestrator import StageContext, run


@pytest.fixture()
def tiny_csv(tmp_path):
    path = tmp_path / "input.csv"
    pd.DataFrame({"a": [1, 2, None], "b": ["x", "y", "z"]}).to_csv(path, index=False)
    return path


def test_dummy_run_artifacts_and_event_order(tiny_csv, tmp_path):
    seen = {}

    def stage_one(ctx: StageContext):
        out = ctx.run_dir / "01_clean_data.csv"
        out.write_text(ctx.data_csv.read_text())
        return Handoff(csv_path=out, report_markdown="# stage one report")

    def stage_two(ctx: StageContext):
        seen["upstream"] = ctx.upstream
        return None  # a stage may produce no handoff

    run_dir = run(tiny_csv, [("one", stage_one), ("two", stage_two)],
                  runs_root=tmp_path / "runs", echo=False)

    # run-dir + snapshot
    assert run_dir.is_dir()
    snapshot = run_dir / "00_raw_data.csv"
    assert snapshot.read_text() == tiny_csv.read_text()  # byte-equal copy

    # ordered events
    types = [e["type"] for e in read_events(run_dir / "events.jsonl")]
    assert types == [ev.RUN_META, ev.STAGE_START, ev.HANDOFF, ev.STAGE_END,
                     ev.STAGE_START, ev.STAGE_END]

    # stage two received stage one's handoff
    assert seen["upstream"].report_markdown == "# stage one report"
    assert seen["upstream"].csv_path == run_dir / "01_clean_data.csv"


def test_run_meta_fingerprint_is_generic_and_correct(tiny_csv, tmp_path):
    run_dir = run(tiny_csv, [], runs_root=tmp_path / "runs", echo=False)
    meta = read_events(run_dir / "events.jsonl")[0]
    fp = meta["payload"]["fingerprint"]
    assert (fp["rows"], fp["cols"]) == (3, 2)
    by_name = {c["name"]: c for c in fp["columns"]}
    assert by_name["a"]["missing_frac"] == round(1 / 3, 4)
    assert by_name["b"]["missing_frac"] == 0.0
    assert meta["payload"]["stages"] == []


def test_failing_stage_logs_error_and_reraises(tiny_csv, tmp_path):
    def boom(ctx):
        raise RuntimeError("kapow")

    with pytest.raises(RuntimeError, match="kapow"):
        run(tiny_csv, [("bad", boom)], runs_root=tmp_path / "runs", echo=False)

    runs = list((tmp_path / "runs").iterdir())
    assert len(runs) == 1
    events = read_events(runs[0] / "events.jsonl")
    types = [e["type"] for e in events]
    assert types == [ev.RUN_META, ev.STAGE_START, ev.ERROR, ev.STAGE_END]
    assert events[-1]["payload"]["status"] == "failed"
    assert "kapow" in events[-2]["payload"]["message"]


def test_echo_mirrors_events_to_stdout(tiny_csv, tmp_path, capsys):
    run(tiny_csv, [], runs_root=tmp_path / "runs", echo=True)
    out = capsys.readouterr().out
    assert "[orchestrator] ▶ run start" in out
