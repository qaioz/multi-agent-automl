"""EventLog — the single source of truth for what happened in a run (SHOW-WORK).

Every decision, tool call, and execution lands here as one JSON object per line
in runs/<ts>/events.jsonl. Console output and the Streamlit UI (live + replay)
are renderers of these same bytes — they can never drift from the truth.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# The 9 event types (spec §4; stage_start/end is one pair).
RUN_META = "run_meta"
STAGE_START = "stage_start"
STAGE_END = "stage_end"
TOOL_CALL = "tool_call"
TOOL_RESULT = "tool_result"
REASONING = "reasoning"
EXECUTION = "execution"
ITERATION_METRICS = "iteration_metrics"
HANDOFF = "handoff"
ERROR = "error"

EVENT_TYPES = frozenset({
    RUN_META, STAGE_START, STAGE_END, TOOL_CALL, TOOL_RESULT,
    REASONING, EXECUTION, ITERATION_METRICS, HANDOFF, ERROR,
})


class EventLog:
    """Append-only writer of events.jsonl. One JSON object per line, flushed
    per event so a live UI can tail the file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, agent: str, type: str, **payload: Any) -> dict:
        if type not in EVENT_TYPES:
            raise ValueError(f"unknown event type {type!r}; expected one of {sorted(EVENT_TYPES)}")
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "type": type,
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        return event


def read_events(path: str | Path) -> list[dict]:
    """Read all complete events from an events.jsonl. Tolerates a trailing
    partial line (live tailing can catch a mid-write)."""
    events = []
    p = Path(path)
    if not p.exists():
        return events
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # partial trailing line
    return events
