"""Console renderer — one readable line per event, for headless runs.

A renderer of events.jsonl bytes, exactly like the UI (DESIGN §4); it adds no
information of its own.
"""

from __future__ import annotations

import json

from . import events as ev

_MAX = 160  # truncate long payload text in console lines


def _short(text: object, limit: int = _MAX) -> str:
    s = str(text).replace("\n", " ⏎ ")
    return s if len(s) <= limit else s[: limit - 1] + "…"


def render(event: dict) -> str:
    """Format one event as a compact human-readable console line."""
    agent = event.get("agent", "?")
    p = event.get("payload", {})
    t = event.get("type")
    body: str
    if t == ev.RUN_META:
        body = f"▶ run start — {_short(json.dumps(p, ensure_ascii=False))}"
    elif t == ev.STAGE_START:
        body = f"━━ stage start: {p.get('stage', '?')} ━━"
    elif t == ev.STAGE_END:
        body = f"━━ stage end: {p.get('stage', '?')} ({p.get('status', '?')}) ━━"
    elif t == ev.TOOL_CALL:
        body = f"🧰 {p.get('tool', '?')}({_short(json.dumps(p.get('args', {}), ensure_ascii=False), 100)})"
    elif t == ev.TOOL_RESULT:
        body = f"↩ {p.get('tool', '?')} → {_short(p.get('result', ''))}"
    elif t == ev.REASONING:
        body = f"💭 {_short(p.get('text', ''))}"
    elif t == ev.EXECUTION:
        rc = p.get("returncode")
        stderr = p.get("stderr") or ""
        tail = f" ⚠ stderr: {_short(stderr, 80)}" if stderr.strip() else ""
        body = f"⚙ execution #{p.get('iteration', '?')} rc={rc} stdout: {_short(p.get('stdout', ''), 80)}{tail}"
    elif t == ev.ITERATION_METRICS:
        body = f"📊 iter {p.get('iteration', '?')}: {_short(json.dumps(p.get('metrics', {}), ensure_ascii=False), 100)}"
    elif t == ev.HANDOFF:
        body = f"🤝 handoff → {p.get('csv_path', '?')} (+ report, {len(p.get('report_markdown', ''))} chars)"
    elif t == ev.ERROR:
        body = f"❗ {_short(p.get('message', ''))}"
    else:
        body = _short(json.dumps(p, ensure_ascii=False))
    return f"[{agent}] {body}"
