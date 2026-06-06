"""Shared base for stage toolsets: the working dataframe + the common verbs.

NO-HARDCODE: everything here is generic; columns and parameters only ever
arrive as agent-chosen arguments.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ..agent import ToolDef

_SAMPLE_VALUES = 5

COLUMN_PARAM = {
    "type": "STRING",
    "description": "Exact column name, copied from tool output (mind spaces/unicode).",
}


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def is_texty(col: pd.Series) -> bool:
    return (pd.api.types.is_string_dtype(col) or pd.api.types.is_object_dtype(col)
            or isinstance(col.dtype, pd.CategoricalDtype))


class DataFrameTools:
    """Holds a stage's working dataframe; exposes the verbs shared by stages."""

    def __init__(self, csv_path: str | Path):
        self.df = pd.read_csv(csv_path)

    def _require_column(self, column: str) -> str:
        if column not in self.df.columns:
            raise ValueError(
                f"unknown column {column!r}. Columns (copy exactly, incl. any "
                f"spaces/unicode): {list(self.df.columns)}"
            )
        return column

    def inspect_metadata(self) -> str:
        df = self.df
        return dumps({
            "rows": int(df.shape[0]),
            "cols": int(df.shape[1]),
            "columns": [
                {
                    "name": c,
                    "dtype": str(df[c].dtype),
                    "missing": int(df[c].isna().sum()),
                    "missing_frac": round(float(df[c].isna().mean()), 4),
                    "nunique": int(df[c].nunique()),
                    "sample_values": [v for v in df[c].dropna().unique()[:_SAMPLE_VALUES]],
                }
                for c in df.columns
            ],
        })

    def drop_column(self, column: str) -> str:
        self._require_column(column)
        self.df = self.df.drop(columns=[column])
        return dumps({"dropped": column, "remaining_cols": int(self.df.shape[1])})

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        self.df.to_csv(path, index=False)
        return path

    def _shared_tooldefs(self) -> list[ToolDef]:
        return [
            ToolDef("inspect_metadata",
                    "Overview of the working dataframe: shape and, per column, dtype, "
                    "missing count/fraction, distinct count and sample values.",
                    {"type": "OBJECT", "properties": {}},
                    self.inspect_metadata),
            ToolDef("drop_column",
                    "Remove one column from the working dataframe.",
                    {"type": "OBJECT", "properties": {"column": COLUMN_PARAM},
                     "required": ["column"]},
                    self.drop_column),
        ]
