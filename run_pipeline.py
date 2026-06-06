"""One-command headless pipeline run.

    uv run python run_pipeline.py --data data/IT_Salary_Survey_EU_2020.csv

Runs the full autonomous team — Cleaner -> Feature Engineer -> Trainer ->
Report — on the given CSV with zero human input. Every event lands in
runs/<ts>/events.jsonl; watch live or replay with `streamlit run ui.py`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from automl_team.orchestrator import run
from automl_team.report import report_stage
from automl_team.stages import cleaner_stage, fe_stage, trainer_stage

STAGES = [
    ("cleaner", cleaner_stage),
    ("feature_engineer", fe_stage),
    ("trainer", trainer_stage),
    ("report", report_stage),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="path to the input CSV")
    parser.add_argument("--runs-root", default="runs", help="where run dirs are created")
    args = parser.parse_args()

    data = Path(args.data)
    if not data.exists():
        print(f"error: {data} does not exist", file=sys.stderr)
        return 2

    run_dir = run(data, STAGES, runs_root=args.runs_root)

    print("\n=== pipeline complete ===")
    print(f"run dir: {run_dir}")
    for artifact in sorted(p.name for p in run_dir.iterdir()):
        print(f"  {artifact}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
