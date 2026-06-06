"""The handoff contract between stages (DESIGN §1).

HANDOFF n = {csv_path, report_markdown}: the next agent's prompt embeds the
report verbatim; its tools operate on a dataframe loaded from the CSV.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Handoff:
    csv_path: Path
    report_markdown: str

    def as_event_payload(self) -> dict:
        return {"csv_path": str(self.csv_path), "report_markdown": self.report_markdown}
