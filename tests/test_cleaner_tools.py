"""u06 — Cleaner toolset driven directly on the real committed CSV (no LLM)."""

import json
from pathlib import Path

import pandas as pd
import pytest

from automl_team.tools.cleaner import IMPUTE_STRATEGIES, CleanerTools

CSV = Path(__file__).resolve().parent.parent / "data" / "IT_Salary_Survey_EU_2020.csv"
CYR = "Сontract duration"   # first char is Cyrillic С (U+0421) — real dataset dirt
SALARY = "Yearly brutto salary (without bonus and stocks) in EUR"


@pytest.fixture()
def tools() -> CleanerTools:
    return CleanerTools(CSV)


def test_inspect_metadata_lists_dirt_columns(tools):
    meta = json.loads(tools.inspect_metadata())
    assert (meta["rows"], meta["cols"]) == (1246, 23)
    names = [c["name"] for c in meta["columns"]]
    assert CYR in names and "Position " in names
    kurz = next(c for c in meta["columns"] if "Kurzarbeit" in c["name"])
    assert kurz["missing_frac"] > 0.6
    assert all(len(c["sample_values"]) <= 5 for c in meta["columns"])


def test_column_stats_cyrillic_round_trip(tools):
    stats = json.loads(tools.get_column_stats(CYR))
    assert stats["column"] == CYR
    assert stats["top_values"]  # categorical → value counts
    assert stats["missing"] > 0


def test_column_stats_numeric(tools):
    stats = json.loads(tools.get_column_stats(SALARY))
    assert stats["stats"]["max"] >= 1e8  # the famous outliers, pre-clean
    assert stats["stats"]["50%"] < 200_000


def test_unknown_column_error_lists_columns(tools):
    with pytest.raises(ValueError, match="unknown column"):
        tools.get_column_stats("Contract duration")  # ASCII C — the hardcode trap


def test_impute_mode_on_cyrillic_column(tools):
    missing = json.loads(tools.get_column_stats(CYR))["missing"]
    result = json.loads(tools.impute_missing(CYR, "mode"))
    assert result["filled"] == missing > 0
    assert json.loads(tools.get_column_stats(CYR))["missing"] == 0


def test_impute_median_numeric_and_constant(tools):
    bonus = next(c for c in json.loads(tools.inspect_metadata())["columns"]
                 if c["dtype"] != "object" and c["missing"] > 0)["name"]
    assert json.loads(tools.impute_missing(bonus, "median"))["filled"] > 0
    result = json.loads(tools.impute_missing(CYR, "constant", value="unknown"))
    assert result["fill_value"] == "unknown"


def test_impute_errors(tools):
    with pytest.raises(ValueError, match="unknown strategy"):
        tools.impute_missing(CYR, "interpolate")
    with pytest.raises(ValueError, match="needs a numeric column"):
        tools.impute_missing(CYR, "median")
    with pytest.raises(ValueError, match="requires the 'value'"):
        tools.impute_missing(CYR, "constant")
    assert "interpolate" not in IMPUTE_STRATEGIES


def test_drop_rows_numeric_outliers(tools):
    result = json.loads(tools.drop_rows(SALARY, "> 1e8"))
    assert result["rows_dropped"] >= 1
    assert json.loads(tools.get_column_stats(SALARY))["stats"]["max"] < 1e8


def test_drop_rows_isna_and_string_eq(tools):
    before = tools.df.shape[0]
    dropped = json.loads(tools.drop_rows(SALARY, "isna"))["rows_dropped"]
    assert dropped == before - tools.df.shape[0]
    city = json.loads(tools.drop_rows("City", "== 'Berlin'"))
    assert city["rows_dropped"] > 100  # Berlin is the biggest city in the data


def test_drop_rows_bad_conditions(tools):
    with pytest.raises(ValueError, match="bad condition"):
        tools.drop_rows("City", "contains Berlin")
    with pytest.raises(ValueError, match="cannot parse literal"):
        tools.drop_rows("City", "== Berlin")  # unquoted string


def test_drop_rows_numeric_literal_on_object_column(tools):
    # numeric comparison must work even if pandas read the column as object
    result = json.loads(tools.drop_rows("Number of vacation days", "> 300"))
    assert result["rows_dropped"] >= 1  # the 365-day vacation claims


def test_normalize_strip_casefold_shrinks_seniority(tools):
    before = json.loads(tools.get_column_stats("Seniority level"))["nunique"]
    result = json.loads(tools.normalize_categories("Seniority level"))
    assert result["nunique_after"] < before <= 23 + 1


def test_normalize_mapping(tools):
    mapping = json.dumps({"Berlin": "BER"})
    result = json.loads(tools.normalize_categories("City", mapping=mapping))
    assert result["mode"] == "mapping"
    assert "BER" in tools.df["City"].values and "Berlin" not in tools.df["City"].values


def test_normalize_rejects_numeric_and_bad_json(tools):
    with pytest.raises(ValueError, match="not categorical/text"):
        tools.normalize_categories(SALARY)
    with pytest.raises(ValueError, match="not valid JSON"):
        tools.normalize_categories("City", mapping="{oops}")


def test_drop_column_and_save_round_trip(tools, tmp_path):
    tools.drop_column("Position ")
    out = tools.save(tmp_path / "clean.csv")
    reloaded = pd.read_csv(out)
    assert "Position " not in reloaded.columns
    assert CYR in reloaded.columns  # unicode survives the save


def test_tooldefs_cover_spec_and_bind(tools):
    defs = {t.name: t for t in tools.tooldefs()}
    assert set(defs) == {"inspect_metadata", "get_column_stats", "impute_missing",
                         "drop_column", "drop_rows", "normalize_categories"}
    # declarations are callable straight through fn (as the agent loop does)
    assert json.loads(defs["inspect_metadata"].fn())["rows"] == 1246
    for t in defs.values():
        assert t.parameters["type"] == "OBJECT" and t.description
