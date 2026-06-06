"""Stage wiring: one function per pipeline stage, run by the orchestrator.

Each stage builds its toolset over the incoming CSV, runs the generic agent
loop, persists the stage artifacts and returns the Handoff. Plumbing only —
the decisions inside the run belong to the agent.
"""

from __future__ import annotations

import dataclasses
import json
import re

from . import events as ev
from .agent import run_agent
from .handoff import Handoff
from .orchestrator import StageContext
from .prompts.cleaner import CLEANER_SYSTEM
from .prompts.features import FEATURE_ENGINEER_SYSTEM
from .prompts.trainer import TRAINER_SYSTEM
from .tools.cleaner import CleanerTools
from .tools.features import FeatureTools
from .tools.sandbox import Sandbox

MIN_EXECUTIONS = 2
MAX_EXECUTIONS = 6

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


FE_TASK_TEMPLATE = (
    "Engineer features on the cleaned dataset in your working dataframe. Start by "
    "inspecting its metadata. Remember the protocol: every tool call must be accompanied "
    "by a short plain-text sentence of rationale, and every mutation must be justified by "
    "tool output from an earlier turn. Finish with your strategy report.\n\n"
    "The Cleaner's handoff report:\n\n{upstream_report}"
)


def fe_stage(ctx: StageContext) -> Handoff:
    if ctx.upstream is None:
        raise ValueError("feature_engineer stage requires the cleaner's handoff")
    tools = FeatureTools(ctx.upstream.csv_path)
    result = run_agent(
        agent_name="feature_engineer",
        system_prompt=FEATURE_ENGINEER_SYSTEM,
        task=FE_TASK_TEMPLATE.format(upstream_report=ctx.upstream.report_markdown),
        tools=tools.tooldefs(),
        log=ctx.log,
        max_turns=60,
    )
    csv_path = ctx.run_dir / "02_engineered_data.csv"
    tools.save(csv_path)
    report = result.report_markdown if result.finished else (
        "# Feature engineering report\n\n(agent hit the turn cap before finishing; "
        "the dataframe state at cap was saved — see events.jsonl for its work)"
    )
    (ctx.run_dir / "02_strategy_report.md").write_text(report, encoding="utf-8")
    return Handoff(csv_path=csv_path, report_markdown=report)


_METRICS_RE = re.compile(r"^METRICS_JSON:\s*(\{.*\})\s*$", re.MULTILINE)

TRAINER_TASK_TEMPLATE = (
    "Train and evaluate an XGBoost model on the engineered dataset. The CSV file is "
    "{csv_name!r} in your working directory. Follow the protocol: state your target/framing "
    "choice first; after every execution, quote its output before reacting; every script "
    "prints its METRICS_JSON line; at least {min_ex} and at most {max_ex} executions.\n\n"
    "The Feature Engineer's strategy report:\n\n{upstream_report}"
)


def parse_metrics_line(stdout: str) -> dict | None:
    """Extract the agent-printed METRICS_JSON payload from stdout, or None.

    Orchestration only: the values were computed and printed by the agent's
    executed code; the harness just files them.
    """
    m = None
    for m in _METRICS_RE.finditer(stdout):  # last marker wins
        pass
    if m is None:
        return None
    try:
        payload = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return {"params": payload.get("params", {}), "metrics": payload.get("metrics", {})}


def trainer_stage(ctx: StageContext) -> Handoff:
    if ctx.upstream is None:
        raise ValueError("trainer stage requires the feature engineer's handoff")
    sandbox = Sandbox(ctx.run_dir, ctx.log, agent_name="trainer")
    history_path = ctx.run_dir / "03_metrics_history.json"
    history: list[dict] = []

    def execute(code: str) -> str:
        if sandbox.executions >= MAX_EXECUTIONS:
            return (
                f"Error: execution budget exhausted ({MAX_EXECUTIONS} runs). No more "
                f"executions are allowed. Call finish(report_markdown) now, reporting "
                f"your best iteration."
            )
        result = sandbox.execute_python_code(code)
        raw = sandbox.last or {}
        parsed = parse_metrics_line(raw.get("stdout", ""))
        if parsed is not None:
            entry = {"iteration": raw.get("iteration"), **parsed}
            history.append(entry)
            history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False),
                                    encoding="utf-8")
            ctx.log.emit("trainer", ev.ITERATION_METRICS, **entry)
        elif raw.get("returncode") == 0:
            result += (
                "\n[harness] note: no parseable METRICS_JSON line was found in stdout — "
                "your next script must print it (one line, valid JSON)."
            )
        remaining = MAX_EXECUTIONS - sandbox.executions
        result += f"\n[harness] executions used: {sandbox.executions}/{MAX_EXECUTIONS} ({remaining} left)."
        return result

    def finish_guard(report: str) -> str | None:
        if sandbox.executions < MIN_EXECUTIONS:
            return (
                f"you have executed code {sandbox.executions} time(s); the protocol "
                f"requires at least {MIN_EXECUTIONS} executions (iterate on your model — "
                f"read your output and react) before finishing"
            )
        return None

    base = sandbox.tooldef()
    # flash mangles large code strings in free-form calls (MALFORMED_FUNCTION_CALL),
    # so the trainer runs with forced function calling; the harness-reserved
    # 'reasoning' argument carries the read-output-react text instead of text parts.
    parameters = {
        "type": "OBJECT",
        "properties": {
            "reasoning": {
                "type": "STRING",
                "description": (
                    "REQUIRED FIRST: if there was a previous execution, quote at least "
                    "one concrete number or error line from its output verbatim and "
                    "state what it implies; then say what this script does/changes "
                    "and why."
                ),
            },
            **base.parameters["properties"],
        },
        "required": ["reasoning", "code"],
    }
    tool = dataclasses.replace(base, parameters=parameters, fn=execute)
    result = run_agent(
        agent_name="trainer",
        system_prompt=TRAINER_SYSTEM,
        task=TRAINER_TASK_TEMPLATE.format(
            csv_name=ctx.upstream.csv_path.name, min_ex=MIN_EXECUTIONS,
            max_ex=MAX_EXECUTIONS, upstream_report=ctx.upstream.report_markdown,
        ),
        tools=[tool],
        log=ctx.log,
        max_turns=30,
        finish_guard=finish_guard,
        force_function_calling=True,
    )
    report = result.report_markdown if result.finished else (
        "# Trainer report\n\n(agent hit the turn cap before finishing; see "
        "events.jsonl and 03_metrics_history.json for its iterations)"
    )
    (ctx.run_dir / "03_trainer_report.md").write_text(report, encoding="utf-8")
    return Handoff(csv_path=ctx.upstream.csv_path, report_markdown=report)
