"""The Trainer's sandbox: execute agent-generated Python in a subprocess.

Fresh interpreter (the project venv's, so generated code sees pandas/xgboost),
run dir as cwd, hard timeout, stdout/stderr captured. The full verbatim output
goes into the `execution` event (SHOW-WORK); what returns to the agent is
head+tail truncated per stream to keep context affordable. A timeout comes
back *as stderr text* so the agent reacts to it like any other error
(DESIGN §3). Accepted risk per spec: runs as the local user — our prompts,
our machine.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .. import events as ev
from ..agent import ToolDef
from ..events import EventLog

DEFAULT_TIMEOUT = 120
_RETURN_CAP = 4000  # per stream, in what the agent sees (event keeps it all)


def _truncate(text: str, cap: int = _RETURN_CAP) -> str:
    if len(text) <= cap:
        return text
    head, tail = text[: cap // 2], text[-cap // 2:]
    omitted = len(text) - cap
    return f"{head}\n… [{omitted} chars omitted — full output is in the log] …\n{tail}"


class Sandbox:
    """Runs code for one Trainer session; counts executions for the guardrails."""

    def __init__(self, run_dir: str | Path, log: EventLog, agent_name: str = "trainer",
                 timeout: int = DEFAULT_TIMEOUT):
        self.run_dir = Path(run_dir)
        self.log = log
        self.agent_name = agent_name
        self.timeout = timeout
        self.executions = 0

    def execute_python_code(self, code: str) -> str:
        self.executions += 1
        n = self.executions
        code_file = self.run_dir / f"code_iter_{n}.py"
        code_file.write_text(code, encoding="utf-8")

        try:
            proc = subprocess.run(
                [sys.executable, code_file.name],
                cwd=self.run_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            returncode, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as e:
            def _s(x) -> str:
                return x.decode(errors="replace") if isinstance(x, bytes) else (x or "")
            returncode = -1
            stdout = _s(e.stdout)
            stderr = _s(e.stderr) + (
                f"\nTimeoutError: execution exceeded the {self.timeout}s limit and was "
                f"killed. Make the code faster (smaller search space, fewer estimators, "
                f"no waiting/loops) and try again."
            )

        self.log.emit(
            self.agent_name, ev.EXECUTION,
            iteration=n, returncode=returncode, stdout=stdout, stderr=stderr,
            code_file=code_file.name,
        )
        return (
            f"returncode: {returncode}\n"
            f"--- stdout ---\n{_truncate(stdout)}\n"
            f"--- stderr ---\n{_truncate(stderr)}"
        )

    def tooldef(self) -> ToolDef:
        return ToolDef(
            "execute_python_code",
            "Execute a Python script in a sandbox (fresh interpreter, this run's "
            "directory as working directory, pandas/xgboost/scikit-learn available, "
            f"{self.timeout}s hard timeout). Returns the return code and the verbatim "
            "stdout/stderr. print() everything you need to see.",
            {"type": "OBJECT", "properties": {
                "code": {"type": "STRING", "description": "the complete Python script"},
            }, "required": ["code"]},
            self.execute_python_code,
        )
