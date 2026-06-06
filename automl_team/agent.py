"""The ONE generic function-calling agent loop (DESIGN §2).

Three agents, one implementation: only (system prompt, toolset, task) differ.
Raw google-genai manual function calling — every arrow is our code, so every
arrow emits an event (SHOW-WORK by construction).

The harness never makes a data decision here: it sends tool declarations,
executes whatever call the model chooses, and feeds the result back. Malformed
or unknown calls are returned *as the tool result* so the agent self-corrects —
the same feedback principle as the Trainer's execute loop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from google.genai import types

from . import events as ev
from .events import EventLog
from .llm import get_client, get_model

FINISH = "finish"
DEFAULT_MAX_TURNS = 30


@dataclass
class ToolDef:
    """One tool: JSON-schema declaration + the Python function that runs it."""

    name: str
    description: str
    parameters: dict          # JSON schema (OBJECT) for the arguments
    fn: Callable[..., Any]    # called with the model's arguments as kwargs


@dataclass
class AgentResult:
    finished: bool                    # True iff the agent called finish()
    report_markdown: str = ""         # finish(report_markdown) payload
    turns: int = 0
    history: list = field(default_factory=list)


_FINISH_DECLARATION = types.FunctionDeclaration(
    name=FINISH,
    description=(
        "Call this exactly once, when your task is complete, with your final "
        "markdown report. This ends your session."
    ),
    parameters={
        "type": "OBJECT",
        "properties": {
            "report_markdown": {
                "type": "STRING",
                "description": "Your final markdown report for this stage.",
            }
        },
        "required": ["report_markdown"],
    },
)


def run_agent(
    agent_name: str,
    system_prompt: str,
    task: str,
    tools: list[ToolDef],
    log: EventLog,
    max_turns: int = DEFAULT_MAX_TURNS,
    finish_guard: Optional[Callable[[str], Optional[str]]] = None,
) -> AgentResult:
    """Run one agent to completion.

    finish_guard(report_markdown) -> error string to *reject* the finish call
    (returned to the agent as the tool result — e.g. the Trainer's
    min-2-executions rule), or None to accept it.
    """
    client = get_client()
    model = get_model()
    by_name = {t.name: t for t in tools}
    if FINISH in by_name:
        raise ValueError("'finish' is harness-owned; do not define it as a tool")

    declarations = [
        types.FunctionDeclaration(name=t.name, description=t.description, parameters=t.parameters)
        for t in tools
    ] + [_FINISH_DECLARATION]
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[types.Tool(function_declarations=declarations)],
    )

    history: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=task)])
    ]

    for turn in range(1, max_turns + 1):
        response = client.models.generate_content(model=model, contents=history, config=config)

        candidate = response.candidates[0] if response.candidates else None
        parts = list(candidate.content.parts or []) if candidate and candidate.content else []
        if not parts:
            log.emit(agent_name, ev.ERROR, message=f"model returned no parts (turn {turn})")
            history.append(types.Content(role="user", parts=[types.Part(
                text="Your last reply was empty. Continue your task: call a tool, "
                     "or call finish(report_markdown) if you are done."
            )]))
            continue

        history.append(candidate.content)

        # Text parts = the agent's visible reasoning (SHOW-WORK).
        for part in parts:
            if part.text:
                log.emit(agent_name, ev.REASONING, text=part.text)

        calls = [p.function_call for p in parts if p.function_call]
        if not calls:
            # Pure text, no call: remind the agent how to act (as a user turn).
            history.append(types.Content(role="user", parts=[types.Part(
                text="Noted. Now act: call a tool, or call finish(report_markdown) "
                     "if your task is complete."
            )]))
            continue

        response_parts: list[types.Part] = []
        for call in calls:
            name = call.name or "?"
            args = dict(call.args or {})
            log.emit(agent_name, ev.TOOL_CALL, tool=name, args=args)

            if name == FINISH:
                report = str(args.get("report_markdown", ""))
                rejection = finish_guard(report) if finish_guard else None
                if rejection is None:
                    log.emit(agent_name, ev.TOOL_RESULT, tool=FINISH, result="accepted")
                    return AgentResult(
                        finished=True, report_markdown=report, turns=turn, history=history
                    )
                result_str = f"finish rejected: {rejection}"
            elif name not in by_name:
                result_str = (
                    f"Error: unknown tool {name!r}. Available tools: "
                    f"{sorted(by_name)} and '{FINISH}'."
                )
            else:
                try:
                    result = by_name[name].fn(**args)
                    result_str = result if isinstance(result, str) else json.dumps(
                        result, ensure_ascii=False, default=str
                    )
                except TypeError as e:  # malformed/missing arguments
                    result_str = f"Error: bad arguments for {name}: {e}"
                except Exception as e:  # tool ran and failed — agent must react
                    result_str = f"Error: {type(e).__name__}: {e}"

            log.emit(agent_name, ev.TOOL_RESULT, tool=name, result=result_str)
            response_parts.append(
                types.Part.from_function_response(name=name, response={"result": result_str})
            )

        history.append(types.Content(role="user", parts=response_parts))

    log.emit(agent_name, ev.ERROR, message=f"turn cap ({max_turns}) reached without finish")
    return AgentResult(finished=False, turns=max_turns, history=history)
