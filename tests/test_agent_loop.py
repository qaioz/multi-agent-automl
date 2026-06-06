"""u05 — generic agent loop tests.

The live test runs one real flash-model round-trip (toy tool → finish) and is
skipped without a GEMINI_API_KEY, so the suite stays green keyless.
"""

import os

import pytest

from automl_team import events as ev
from automl_team.agent import FINISH, ToolDef, run_agent
from automl_team.events import EventLog, read_events

needs_key = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"), reason="no GEMINI_API_KEY in env/.env"
)


def reverse_tool(calls: list) -> ToolDef:
    def fn(text: str) -> str:
        calls.append(text)
        return text[::-1]

    return ToolDef(
        name="reverse_string",
        description="Reverse a string and return it.",
        parameters={
            "type": "OBJECT",
            "properties": {"text": {"type": "STRING", "description": "string to reverse"}},
            "required": ["text"],
        },
        fn=fn,
    )


def test_finish_is_harness_owned(tmp_path):
    bad = ToolDef(name=FINISH, description="x", parameters={"type": "OBJECT", "properties": {}},
                  fn=lambda: "")
    with pytest.raises(ValueError, match="harness-owned"):
        run_agent("toy", "s", "t", [bad], EventLog(tmp_path / "e.jsonl"))


@needs_key
def test_toy_agent_full_round_trip(tmp_path):
    log_path = tmp_path / "events.jsonl"
    calls: list = []

    result = run_agent(
        agent_name="toy",
        system_prompt=(
            "You are a test agent. You MUST use your tools for any string operation — "
            "never compute results yourself. IMPORTANT: in every response that calls a "
            "tool, also include a short plain-text sentence explaining WHY, before the "
            "call. When done, call finish with a one-line markdown report."
        ),
        task=(
            "Reverse the string 'automl' using your tool, then finish, stating the "
            "result. Remember: each tool call must be accompanied by one sentence of "
            "plain-text rationale."
        ),
        tools=[reverse_tool(calls)],
        log=EventLog(log_path),
        max_turns=6,
    )

    # Loop completed via finish, tool really ran (invariants, not exact
    # sequences — the model may legitimately vary its path)
    assert result.finished
    assert "automl" in calls
    assert result.report_markdown.strip()

    events = read_events(log_path)
    types = [e["type"] for e in events]

    # every arrow logged: ≥1 reverse_string call before finish, its verbatim
    # result, and finish acceptance as the final event
    tool_seq = [e["payload"]["tool"] for e in events if e["type"] == ev.TOOL_CALL]
    assert "reverse_string" in tool_seq and tool_seq[-1] == FINISH, tool_seq
    assert tool_seq.index("reverse_string") < tool_seq.index(FINISH)
    results = [e["payload"] for e in events if e["type"] == ev.TOOL_RESULT]
    assert any(r["tool"] == "reverse_string" and r["result"] == "lmotua" for r in results)
    assert events[-1]["payload"] == {"tool": FINISH, "result": "accepted"}

    # reasoning text captured (prompt demands a stated plan)
    assert any(e["type"] == ev.REASONING and e["payload"]["text"].strip() for e in events), types


@needs_key
def test_finish_guard_rejection_feeds_back(tmp_path):
    """A rejected finish must come back as a tool result the agent reacts to."""
    log_path = tmp_path / "events.jsonl"
    rejections: list = []

    def guard(report: str):
        if not rejections:
            rejections.append(report)
            return "you must call reverse_string at least once before finishing"
        return None

    result = run_agent(
        agent_name="toy",
        system_prompt="You are a test agent. Follow tool results exactly. Be brief.",
        task="Call finish immediately with the report 'done'.",
        tools=[reverse_tool([])],
        log=EventLog(log_path),
        max_turns=8,
        finish_guard=guard,
    )

    assert result.finished
    assert rejections  # first finish was rejected
    events = read_events(log_path)
    rejected = [e for e in events if e["type"] == ev.TOOL_RESULT
                and str(e["payload"]["result"]).startswith("finish rejected")]
    assert rejected, "rejection must be logged as a tool_result"
    # after rejection the agent eventually finished (guard accepted 2nd attempt)
    assert events[-1]["payload"] == {"tool": FINISH, "result": "accepted"}
