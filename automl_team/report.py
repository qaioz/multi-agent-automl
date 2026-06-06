"""Stage 4: one LLM call composes report.md from the run's materials.

No agent loop, no tools — a pure synthesis call. The materials are the three
stage reports, the metrics history and the raw-data fingerprint; the prompt
forbids inventing facts beyond them.
"""

from __future__ import annotations

import json
from pathlib import Path

from .handoff import Handoff
from .llm import get_client, get_model
from .orchestrator import StageContext, _fingerprint
from .prompts.report import REPORT_SYSTEM, REPORT_TASK_TEMPLATE


def _read_or_note(path: Path, what: str) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"({what} is missing for this run)"


def report_stage(ctx: StageContext) -> Handoff:
    run_dir = ctx.run_dir
    history_path = run_dir / "03_metrics_history.json"
    task = REPORT_TASK_TEMPLATE.format(
        fingerprint=json.dumps(_fingerprint(ctx.data_csv), indent=2, ensure_ascii=False),
        cleaner_report=_read_or_note(run_dir / "01_cleaner_report.md", "cleaner report"),
        fe_report=_read_or_note(run_dir / "02_strategy_report.md", "strategy report"),
        trainer_report=_read_or_note(run_dir / "03_trainer_report.md", "trainer report"),
        metrics_history=_read_or_note(history_path, "metrics history"),
    )
    client = get_client()
    response = client.models.generate_content(
        model=get_model(),
        contents=task,
        config={"system_instruction": REPORT_SYSTEM},
    )
    report = (response.text or "").strip()
    if not report:
        raise RuntimeError("report model returned no text")
    (run_dir / "report.md").write_text(report + "\n", encoding="utf-8")
    csv_path = ctx.upstream.csv_path if ctx.upstream else ctx.data_csv
    return Handoff(csv_path=csv_path, report_markdown=report)
