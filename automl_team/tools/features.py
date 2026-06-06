"""Feature-Engineer toolset — generic verbs over the stage's working dataframe.

Same NO-HARDCODE construction as the Cleaner's: every column, operation,
encoding method, rule and threshold is an agent-chosen argument.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from ..agent import ToolDef
from .base import COLUMN_PARAM, DataFrameTools, dumps, is_texty

INTERACTION_OPS = ("add", "subtract", "multiply", "divide")
ENCODE_METHODS = ("onehot", "ordinal", "frequency")
_TOP_PAIRS = 15


def _col_summary(col: pd.Series) -> dict:
    desc = col.describe()
    return {k: round(float(desc[k]), 4) for k in ("mean", "std", "min", "max")
            if k in desc and pd.notna(desc[k])}


class FeatureTools(DataFrameTools):
    """The Feature-Engineer stage's verbs (plus shared metadata/drop/save)."""

    def _numeric(self, column: str) -> pd.Series:
        col = self.df[self._require_column(column)]
        if not pd.api.types.is_numeric_dtype(col):
            coerced = pd.to_numeric(col, errors="coerce")
            n_lost = int(coerced.isna().sum() - col.isna().sum())
            if n_lost > len(col) * 0.5:
                raise ValueError(
                    f"column {column!r} is {col.dtype} and not meaningfully numeric "
                    f"({n_lost} of {len(col)} values fail conversion)"
                )
            return coerced
        return col

    # -- create -----------------------------------------------------------------

    def create_interaction(self, col_a: str, col_b: str, op: str, new_name: str) -> str:
        if op not in INTERACTION_OPS:
            raise ValueError(f"unknown op {op!r}; choose one of {INTERACTION_OPS}")
        if new_name in self.df.columns:
            raise ValueError(f"column {new_name!r} already exists")
        a, b = self._numeric(col_a), self._numeric(col_b)
        if op == "add":
            result = a + b
        elif op == "subtract":
            result = a - b
        elif op == "multiply":
            result = a * b
        else:  # divide — /0 and 0/0 become NaN, never inf
            result = a / b.replace(0, np.nan)
        self.df[new_name] = result
        return dumps({"created": new_name, "op": op, "from": [col_a, col_b],
                      "missing": int(result.isna().sum()), "stats": _col_summary(result)})

    def count_items(self, column: str, sep: str, new_name: str) -> str:
        """New numeric column: number of `sep`-separated items per row (NaN -> 0)."""
        self._require_column(column)
        if new_name in self.df.columns:
            raise ValueError(f"column {new_name!r} already exists")
        col = self.df[column]
        if not is_texty(col):
            raise ValueError(f"column {column!r} is {col.dtype}, not text")
        counts = col.map(
            lambda v: len([p for p in str(v).split(sep) if p.strip()])
            if isinstance(v, str) else 0
        )
        self.df[new_name] = counts
        return dumps({"created": new_name, "from": column, "sep": sep,
                      "stats": _col_summary(counts)})

    def bucketize(self, column: str, rule: str, new_name: str) -> str:
        """rule is a JSON object string: {"edges": [...], "labels": [...]?} for
        fixed bins, or {"quantiles": n} for equal-frequency bins."""
        self._require_column(column)
        if new_name in self.df.columns:
            raise ValueError(f"column {new_name!r} already exists")
        try:
            spec = json.loads(rule)
        except json.JSONDecodeError as e:
            raise ValueError(f"rule is not valid JSON: {e}") from None
        col = self._numeric(column)
        if "edges" in spec:
            labels = spec.get("labels")
            if labels is not None and len(labels) != len(spec["edges"]) - 1:
                raise ValueError("need exactly len(edges)-1 labels")
            bucketed = pd.cut(col, bins=spec["edges"], labels=labels)
        elif "quantiles" in spec:
            bucketed = pd.qcut(col, q=int(spec["quantiles"]), duplicates="drop")
        else:
            raise ValueError('rule must contain "edges" or "quantiles"')
        self.df[new_name] = bucketed.astype(str).replace("nan", np.nan)
        dist = self.df[new_name].value_counts(dropna=True)
        return dumps({"created": new_name, "from": column,
                      "buckets": {str(k): int(v) for k, v in dist.items()}})

    # -- encode -----------------------------------------------------------------

    def encode_categorical(self, column: str, method: str, order: str | None = None) -> str:
        self._require_column(column)
        if method not in ENCODE_METHODS:
            raise ValueError(f"unknown method {method!r}; choose one of {ENCODE_METHODS}")
        col = self.df[column]
        if not is_texty(col):
            raise ValueError(f"column {column!r} is {col.dtype}, not categorical/text")

        if method == "onehot":
            dummies = pd.get_dummies(col, prefix=column, dtype=int)
            self.df = pd.concat([self.df.drop(columns=[column]), dummies], axis=1)
            return dumps({"column": column, "method": method,
                          "new_columns": list(dummies.columns)})
        if method == "ordinal":
            if order is None:
                raise ValueError(
                    "method 'ordinal' requires 'order': a JSON array string of the "
                    "category values, lowest first"
                )
            try:
                ordering = json.loads(order)
            except json.JSONDecodeError as e:
                raise ValueError(f"order is not valid JSON: {e}") from None
            if not isinstance(ordering, list):
                raise ValueError("order must be a JSON array")
            mapping = {v: i for i, v in enumerate(ordering)}
            encoded = col.map(mapping)
            unmapped = int(encoded.isna().sum() - col.isna().sum())
            self.df[column] = encoded
            return dumps({"column": column, "method": method, "mapping": mapping,
                          "unmapped_values_now_nan": unmapped})
        # frequency
        freq = col.value_counts(dropna=True)
        self.df[column] = col.map(freq)
        return dumps({"column": column, "method": method,
                      "distinct_frequencies": int(freq.nunique())})

    # -- analyse / select ---------------------------------------------------------

    def correlation_analysis(self, target: str | None = None) -> str:
        numeric = self.df.select_dtypes(include="number")
        if numeric.shape[1] < 2:
            raise ValueError(
                f"need >=2 numeric columns, have {list(numeric.columns)}; "
                f"encode categoricals first"
            )
        if target is not None:
            self._require_column(target)
            if target not in numeric.columns:
                raise ValueError(f"target {target!r} is not numeric")
            corr = numeric.corr()[target].drop(labels=[target]).dropna()
            ranked = corr.reindex(corr.abs().sort_values(ascending=False).index)
            return dumps({"target": target,
                          "correlations": {k: round(float(v), 4) for k, v in ranked.items()}})
        corr = numeric.corr()
        pairs = (
            corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1))
            .stack().dropna()
        )
        strongest = pairs.reindex(pairs.abs().sort_values(ascending=False).index)
        return dumps({"strongest_pairs": [
            {"a": a, "b": b, "r": round(float(r), 4)}
            for (a, b), r in strongest.head(_TOP_PAIRS).items()
        ]})

    def select_top_features(self, target: str, k: int | None = None,
                            threshold: float | None = None) -> str:
        """Keep the target + the numeric features most |correlated| with it
        (top-k or >= threshold); drop the remaining numeric features."""
        self._require_column(target)
        if (k is None) == (threshold is None):
            raise ValueError("provide exactly one of 'k' or 'threshold'")
        numeric = self.df.select_dtypes(include="number")
        if target not in numeric.columns:
            raise ValueError(f"target {target!r} is not numeric")
        corr = numeric.corr()[target].drop(labels=[target]).abs().dropna()
        if k is not None:
            kept = list(corr.sort_values(ascending=False).head(int(k)).index)
        else:
            kept = list(corr[corr >= float(threshold)].index)
        dropped = [c for c in numeric.columns if c != target and c not in kept]
        self.df = self.df.drop(columns=dropped)
        return dumps({"target": target, "kept": kept, "dropped": dropped,
                      "non_numeric_untouched": [c for c in self.df.columns
                                                if c not in kept and c != target]})

    # -- declarations ----------------------------------------------------------

    def tooldefs(self) -> list[ToolDef]:
        return self._shared_tooldefs() + [
            ToolDef("create_interaction",
                    "Create a new numeric feature combining two columns. "
                    "op: add | subtract | multiply | divide (divide-by-zero -> missing).",
                    {"type": "OBJECT", "properties": {
                        "col_a": COLUMN_PARAM, "col_b": COLUMN_PARAM,
                        "op": {"type": "STRING", "description": "add|subtract|multiply|divide"},
                        "new_name": {"type": "STRING", "description": "name of the new column"},
                     }, "required": ["col_a", "col_b", "op", "new_name"]},
                    self.create_interaction),
            ToolDef("count_items",
                    "Create a numeric column counting separator-delimited items in a text "
                    "column (e.g. how many technologies are listed). Missing -> 0.",
                    {"type": "OBJECT", "properties": {
                        "column": COLUMN_PARAM,
                        "sep": {"type": "STRING", "description": "item separator, e.g. ';'"},
                        "new_name": {"type": "STRING", "description": "name of the new column"},
                     }, "required": ["column", "sep", "new_name"]},
                    self.count_items),
            ToolDef("bucketize",
                    "Bin a numeric column into categories. rule is a JSON object string: "
                    "{\"edges\": [0,30,60], \"labels\": [\"low\",\"high\"]} or {\"quantiles\": 4}.",
                    {"type": "OBJECT", "properties": {
                        "column": COLUMN_PARAM,
                        "rule": {"type": "STRING", "description": "JSON bin rule"},
                        "new_name": {"type": "STRING", "description": "name of the new column"},
                     }, "required": ["column", "rule", "new_name"]},
                    self.bucketize),
            ToolDef("encode_categorical",
                    "Encode a categorical column numerically. method: onehot (replaces the "
                    "column with 0/1 dummies) | ordinal (needs order: JSON array, lowest "
                    "first) | frequency (value -> its count).",
                    {"type": "OBJECT", "properties": {
                        "column": COLUMN_PARAM,
                        "method": {"type": "STRING", "description": "onehot|ordinal|frequency"},
                        "order": {"type": "STRING",
                                  "description": "JSON array of values, only for ordinal"},
                     }, "required": ["column", "method"]},
                    self.encode_categorical),
            ToolDef("correlation_analysis",
                    "Correlations among numeric columns. With target: every feature's "
                    "correlation with it, strongest first. Without: strongest pairs overall.",
                    {"type": "OBJECT", "properties": {
                        "target": {"type": "STRING",
                                   "description": "optional target column name"},
                     }},
                    self.correlation_analysis),
            ToolDef("select_top_features",
                    "Keep only the numeric features most correlated with the target "
                    "(exactly one of k or threshold); weaker numeric features are dropped.",
                    {"type": "OBJECT", "properties": {
                        "target": COLUMN_PARAM,
                        "k": {"type": "INTEGER", "description": "keep the top k features"},
                        "threshold": {"type": "NUMBER",
                                      "description": "keep features with |corr| >= this"},
                     }, "required": ["target"]},
                    self.select_top_features),
        ]
