"""Cleaner toolset — generic verbs over the stage's working dataframe.

NO-HARDCODE lives here by construction: every verb takes the column / strategy /
parameters as arguments chosen by the LLM agent. No dataset column name, no
default strategy, no threshold appears in this source.

All results are returned as strings (JSON, ensure_ascii=False) — they go back
into the agent's context verbatim. Invalid input raises ValueError with the
valid options; the agent loop (u05) feeds that back as the tool result so the
agent self-corrects.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd

from ..agent import ToolDef

_SAMPLE_VALUES = 5
_TOP_CATEGORIES = 20
IMPUTE_STRATEGIES = ("mean", "median", "mode", "constant")
_CONDITION_OPS = (">", ">=", "<", "<=", "==", "!=")


def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


class CleanerTools:
    """Holds the Cleaner stage's working dataframe; exposes the generic verbs."""

    def __init__(self, csv_path: str | Path):
        self.df = pd.read_csv(csv_path)

    # -- helpers -------------------------------------------------------------

    def _require_column(self, column: str) -> str:
        if column not in self.df.columns:
            raise ValueError(
                f"unknown column {column!r}. Columns (copy exactly, incl. any "
                f"spaces/unicode): {list(self.df.columns)}"
            )
        return column

    # -- read tools ----------------------------------------------------------

    def inspect_metadata(self) -> str:
        df = self.df
        return _dumps({
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

    def get_column_stats(self, column: str) -> str:
        col = self.df[self._require_column(column)]
        info: dict = {
            "column": column,
            "dtype": str(col.dtype),
            "missing": int(col.isna().sum()),
            "missing_frac": round(float(col.isna().mean()), 4),
            "nunique": int(col.nunique()),
        }
        if pd.api.types.is_numeric_dtype(col):
            desc = col.describe()
            info["stats"] = {k: float(desc[k]) for k in
                             ("mean", "std", "min", "25%", "50%", "75%", "max")
                             if k in desc and pd.notna(desc[k])}
        else:
            counts = col.value_counts(dropna=True).head(_TOP_CATEGORIES)
            info["top_values"] = {str(k): int(v) for k, v in counts.items()}
            if col.nunique() > _TOP_CATEGORIES:
                info["note"] = f"showing top {_TOP_CATEGORIES} of {col.nunique()} values"
        return _dumps(info)

    # -- write tools ---------------------------------------------------------

    def impute_missing(self, column: str, strategy: str, value: str | None = None) -> str:
        self._require_column(column)
        col = self.df[column]
        n_missing = int(col.isna().sum())
        if strategy not in IMPUTE_STRATEGIES:
            raise ValueError(f"unknown strategy {strategy!r}; choose one of {IMPUTE_STRATEGIES}")
        if n_missing == 0:
            return _dumps({"column": column, "filled": 0, "note": "no missing values"})
        if strategy in ("mean", "median"):
            if not pd.api.types.is_numeric_dtype(col):
                raise ValueError(
                    f"strategy {strategy!r} needs a numeric column; {column!r} is {col.dtype}"
                )
            fill = col.mean() if strategy == "mean" else col.median()
        elif strategy == "mode":
            modes = col.mode(dropna=True)
            if modes.empty:
                raise ValueError(f"column {column!r} has no mode (all values missing)")
            fill = modes.iloc[0]
        else:  # constant
            if value is None:
                raise ValueError("strategy 'constant' requires the 'value' argument")
            fill = value
        self.df[column] = col.fillna(fill)
        return _dumps({"column": column, "strategy": strategy, "fill_value": fill,
                       "filled": n_missing})

    def drop_column(self, column: str) -> str:
        self._require_column(column)
        self.df = self.df.drop(columns=[column])
        return _dumps({"dropped": column, "remaining_cols": int(self.df.shape[1])})

    def drop_rows(self, column: str, condition: str) -> str:
        """Drop rows where `column` matches `condition`.

        condition: 'isna' | '<op> <literal>' with op in > >= < <= == != ,
        e.g. '> 1e8', "== 'yes'". Literals are parsed with ast.literal_eval.
        """
        self._require_column(column)
        cond = condition.strip()
        before = int(self.df.shape[0])
        if cond == "isna":
            mask = self.df[column].isna()
        else:
            op = next((o for o in sorted(_CONDITION_OPS, key=len, reverse=True)
                       if cond.startswith(o)), None)
            if op is None:
                raise ValueError(
                    f"bad condition {condition!r}; use 'isna' or '<op> <literal>' "
                    f"with op in {_CONDITION_OPS}"
                )
            literal_text = cond[len(op):].strip()
            try:
                literal = ast.literal_eval(literal_text)
            except (ValueError, SyntaxError):
                raise ValueError(
                    f"cannot parse literal {literal_text!r} in condition {condition!r}; "
                    f"use a number or a quoted string"
                ) from None
            col = self.df[column]
            if isinstance(literal, (int, float)) and not pd.api.types.is_numeric_dtype(col):
                col = pd.to_numeric(col, errors="coerce")
            mask = {
                ">": col > literal, ">=": col >= literal,
                "<": col < literal, "<=": col <= literal,
                "==": col == literal, "!=": col != literal,
            }[op]
        self.df = self.df[~mask.fillna(False)]
        dropped = before - int(self.df.shape[0])
        return _dumps({"column": column, "condition": cond, "rows_dropped": dropped,
                       "rows_remaining": int(self.df.shape[0])})

    def normalize_categories(self, column: str, mapping: str | None = None) -> str:
        """Without mapping: strip whitespace + casefold every value. With mapping
        (a JSON object string {"old": "new", …}): apply exact replacements."""
        self._require_column(column)
        col = self.df[column]
        is_texty = (pd.api.types.is_string_dtype(col) or pd.api.types.is_object_dtype(col)
                    or isinstance(col.dtype, pd.CategoricalDtype))
        if not is_texty:
            raise ValueError(f"column {column!r} is {col.dtype}, not categorical/text")
        before = int(col.nunique())
        if mapping is not None:
            try:
                replacements = json.loads(mapping)
            except json.JSONDecodeError as e:
                raise ValueError(f"mapping is not valid JSON: {e}") from None
            if not isinstance(replacements, dict):
                raise ValueError("mapping must be a JSON object {\"old\": \"new\", …}")
            self.df[column] = col.replace(replacements)
        else:
            self.df[column] = col.map(
                lambda v: v.strip().casefold() if isinstance(v, str) else v
            )
        after = int(self.df[column].nunique())
        return _dumps({"column": column, "mode": "mapping" if mapping else "strip+casefold",
                       "nunique_before": before, "nunique_after": after})

    # -- persistence + declarations -------------------------------------------

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        self.df.to_csv(path, index=False)
        return path

    def tooldefs(self) -> list[ToolDef]:
        col_param = {"type": "STRING", "description":
                     "Exact column name, copied from tool output (mind spaces/unicode)."}
        return [
            ToolDef("inspect_metadata",
                    "Overview of the working dataframe: shape and, per column, dtype, "
                    "missing count/fraction, distinct count and sample values.",
                    {"type": "OBJECT", "properties": {}},
                    self.inspect_metadata),
            ToolDef("get_column_stats",
                    "Detailed stats for one column: numeric describe() or top value counts.",
                    {"type": "OBJECT", "properties": {"column": col_param},
                     "required": ["column"]},
                    self.get_column_stats),
            ToolDef("impute_missing",
                    "Fill missing values in a column. strategy: one of "
                    "mean|median|mode|constant ('constant' also needs value).",
                    {"type": "OBJECT", "properties": {
                        "column": col_param,
                        "strategy": {"type": "STRING",
                                     "description": "mean | median | mode | constant"},
                        "value": {"type": "STRING",
                                  "description": "fill value, only for strategy=constant"},
                     }, "required": ["column", "strategy"]},
                    self.impute_missing),
            ToolDef("drop_column",
                    "Remove one column from the working dataframe.",
                    {"type": "OBJECT", "properties": {"column": col_param},
                     "required": ["column"]},
                    self.drop_column),
            ToolDef("drop_rows",
                    "Drop rows where the column matches a condition: 'isna' or "
                    "'<op> <literal>' with op in > >= < <= == != (e.g. '> 1e8', \"== 'x'\").",
                    {"type": "OBJECT", "properties": {
                        "column": col_param,
                        "condition": {"type": "STRING",
                                      "description": "'isna' or e.g. '> 1e8', \"== 'yes'\""},
                     }, "required": ["column", "condition"]},
                    self.drop_rows),
            ToolDef("normalize_categories",
                    "Normalize a text/categorical column. Without mapping: strip whitespace "
                    "+ lowercase all values. With mapping: a JSON object string of exact "
                    "replacements {\"old\": \"new\", …}.",
                    {"type": "OBJECT", "properties": {
                        "column": col_param,
                        "mapping": {"type": "STRING",
                                    "description": "optional JSON object of replacements"},
                     }, "required": ["column"]},
                    self.normalize_categories),
        ]
