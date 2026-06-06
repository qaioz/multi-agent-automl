"""Orchestrator — plumbing and logging only, zero data decisions (DESIGN §1).

Creates the run dir, snapshots the raw data with a generic stats fingerprint,
then runs the stages in order, threading each stage's Handoff into the next.
Every data-science decision belongs to the LLM agents inside the stages.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from . import console
from . import events as ev
from .events import EventLog
from .handoff import Handoff


@dataclass
class StageContext:
    """Everything a stage gets from the orchestrator."""

    run_dir: Path
    log: EventLog
    data_csv: Path                      # the raw-data snapshot (00_raw_data.csv)
    upstream: Optional[Handoff] = None  # previous stage's handoff, if any
    extra: dict = field(default_factory=dict)


StageFn = Callable[[StageContext], Optional[Handoff]]


def _fingerprint(csv_path: Path) -> dict:
    """Generic stats fingerprint of a CSV — shape, dtypes, missingness.

    Purely descriptive and dataset-agnostic (no column names appear in code;
    they are read from the file): NO-HARDCODE safe.
    """
    df = pd.read_csv(csv_path)
    return {
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "columns": [
            {
                "name": c,
                "dtype": str(df[c].dtype),
                "missing_frac": round(float(df[c].isna().mean()), 4),
            }
            for c in df.columns
        ],
    }


def run(
    data_csv: str | Path,
    stages: list[tuple[str, StageFn]],
    runs_root: str | Path = "runs",
    echo: bool = True,
    run_meta_extra: dict | None = None,
) -> Path:
    """Run the pipeline: run-dir, raw snapshot, then stages in order.

    Returns the run dir. A stage exception is logged (`error` + failed
    `stage_end`) and re-raised — no silent half-runs.
    """
    data_csv = Path(data_csv)
    run_dir = Path(runs_root) / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir.mkdir(parents=True, exist_ok=False)

    log = EventLog(run_dir / "events.jsonl")

    def emit(agent: str, type: str, **payload):
        event = log.emit(agent, type, **payload)
        if echo:
            print(console.render(event), flush=True)
        return event

    snapshot = run_dir / "00_raw_data.csv"
    shutil.copyfile(data_csv, snapshot)

    emit(
        "orchestrator",
        ev.RUN_META,
        data=str(data_csv),
        run_dir=str(run_dir),
        stages=[name for name, _ in stages],
        fingerprint=_fingerprint(snapshot),
        **(run_meta_extra or {}),
    )

    upstream: Optional[Handoff] = None
    for name, fn in stages:
        emit("orchestrator", ev.STAGE_START, stage=name)
        ctx = StageContext(run_dir=run_dir, log=log, data_csv=snapshot, upstream=upstream)
        try:
            result = fn(ctx)
        except Exception as e:
            emit("orchestrator", ev.ERROR, message=f"stage {name!r} failed: {e}", stage=name)
            emit("orchestrator", ev.STAGE_END, stage=name, status="failed")
            raise
        if isinstance(result, Handoff):
            emit(name, ev.HANDOFF, **result.as_event_payload())
            upstream = result
        emit("orchestrator", ev.STAGE_END, stage=name, status="ok")

    return run_dir
