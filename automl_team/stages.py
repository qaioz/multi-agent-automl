"""Stage wiring: one function per pipeline stage, run by the orchestrator.

Each stage builds its toolset over the incoming CSV, runs the generic agent
loop, persists the stage artifacts and returns the Handoff. Plumbing only —
the decisions inside the run belong to the agent.
"""

from __future__ import annotations

from .agent import run_agent
from .handoff import Handoff
from .orchestrator import StageContext
from .prompts.cleaner import CLEANER_SYSTEM
from .tools.cleaner import CleanerTools

CLEANER_TASK = (
    "Clean the dataset in your working dataframe. Start by inspecting its metadata. "
    "Remember the protocol: every tool call must be accompanied by a short plain-text "
    "sentence of rationale, and every mutation must be justified by tool output you "
    "obtained in an earlier turn. Finish with your handoff report."
)


def cleaner_stage(ctx: StageContext) -> Handoff:
    tools = CleanerTools(ctx.data_csv)
    result = run_agent(
        agent_name="cleaner",
        system_prompt=CLEANER_SYSTEM,
        task=CLEANER_TASK,
        tools=tools.tooldefs(),
        log=ctx.log,
        max_turns=60,
    )
    csv_path = ctx.run_dir / "01_clean_data.csv"
    tools.save(csv_path)
    report = result.report_markdown if result.finished else (
        "# Cleaner report\n\n(agent hit the turn cap before finishing; "
        "the dataframe state at cap was saved — see events.jsonl for its work)"
    )
    (ctx.run_dir / "01_cleaner_report.md").write_text(report, encoding="utf-8")
    return Handoff(csv_path=csv_path, report_markdown=report)
