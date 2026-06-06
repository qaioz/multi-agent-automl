"""u08 — Feature-Engineer toolset driven on the real CSV (no LLM)."""

import json
from pathlib import Path

import pandas as pd
import pytest

from automl_team.tools.features import ENCODE_METHODS, INTERACTION_OPS, FeatureTools

CSV = Path(__file__).resolve().parent.parent / "data" / "IT_Salary_Survey_EU_2020.csv"
SALARY = "Yearly brutto salary (without bonus and stocks) in EUR"
EXP = "Total years of experience"
TECH = "Other technologies/programming languages you use often"


@pytest.fixture()
def tools() -> FeatureTools:
    t = FeatureTools(CSV)
    # cleaned-shape-ish: kill the absurd outliers so correlations are meaningful
    t.df = t.df[pd.to_numeric(t.df[SALARY], errors="coerce") < 500_000]
    return t


def test_create_interaction_divide_guards_zero(tools):
    result = json.loads(tools.create_interaction(SALARY, EXP, "divide", "salary_per_year_exp"))
    assert result["created"] == "salary_per_year_exp"
    col = tools.df["salary_per_year_exp"]
    assert not pd.api.types.is_object_dtype(col)
    assert not (col == float("inf")).any()  # /0 became NaN, not inf
    assert result["stats"]["mean"] > 0


def test_create_interaction_coerces_object_numeric(tools):
    # EXP is text-typed in the raw CSV (free-text answers) — must coerce
    result = json.loads(tools.create_interaction(EXP, "Age", "add", "exp_plus_age"))
    assert result["created"] == "exp_plus_age"


def test_create_interaction_errors(tools):
    with pytest.raises(ValueError, match="unknown op"):
        tools.create_interaction(SALARY, "Age", "power", "x")
    with pytest.raises(ValueError, match="already exists"):
        tools.create_interaction(SALARY, "Age", "add", "Age")
    with pytest.raises(ValueError, match="not meaningfully numeric"):
        tools.create_interaction("City", "Age", "add", "city_age")
    assert "power" not in INTERACTION_OPS


def test_count_items_packed_list(tools):
    result = json.loads(tools.count_items(TECH, ",", "n_techs"))
    col = tools.df["n_techs"]
    assert col.min() >= 0 and col.max() > 3  # some people list many techs
    assert (tools.df[tools.df[TECH].isna()]["n_techs"] == 0).all()
    assert result["stats"]["max"] == col.max()


def test_bucketize_edges_and_quantiles(tools):
    edges = json.dumps({"edges": [0, 30, 45, 100], "labels": ["young", "mid", "senior"]})
    result = json.loads(tools.bucketize("Age", edges, "age_band"))
    assert set(result["buckets"]) <= {"young", "mid", "senior"}
    q = json.loads(tools.bucketize(SALARY, json.dumps({"quantiles": 4}), "salary_q"))
    assert len(q["buckets"]) == 4


def test_bucketize_errors(tools):
    with pytest.raises(ValueError, match="not valid JSON"):
        tools.bucketize("Age", "edges=0,30", "x")
    with pytest.raises(ValueError, match="len\\(edges\\)-1"):
        tools.bucketize("Age", json.dumps({"edges": [0, 30], "labels": ["a", "b"]}), "x")
    with pytest.raises(ValueError, match='"edges" or "quantiles"'):
        tools.bucketize("Age", json.dumps({"bins": 3}), "x")


def test_encode_onehot_replaces_column(tools):
    tools.df["Gender"] = tools.df["Gender"].str.strip().str.lower()
    result = json.loads(tools.encode_categorical("Gender", "onehot"))
    assert "Gender" not in tools.df.columns
    assert all(c.startswith("Gender_") for c in result["new_columns"])
    assert set(tools.df[result["new_columns"][0]].unique()) <= {0, 1}


def test_encode_ordinal_with_order_and_unmapped(tools):
    order = json.dumps(["Junior", "Middle", "Senior", "Lead", "Head"])
    result = json.loads(tools.encode_categorical("Seniority level", "ordinal", order=order))
    assert result["mapping"]["Senior"] == 2
    assert result["unmapped_values_now_nan"] > 0  # the 23-value noise didn't all map
    assert pd.api.types.is_numeric_dtype(tools.df["Seniority level"])


def test_encode_frequency(tools):
    result = json.loads(tools.encode_categorical("City", "frequency"))
    assert pd.api.types.is_numeric_dtype(tools.df["City"])
    assert tools.df["City"].max() > 300  # Berlin count
    assert result["distinct_frequencies"] > 1


def test_encode_errors(tools):
    with pytest.raises(ValueError, match="unknown method"):
        tools.encode_categorical("City", "target")
    with pytest.raises(ValueError, match="requires 'order'"):
        tools.encode_categorical("City", "ordinal")
    with pytest.raises(ValueError, match="not categorical/text"):
        tools.encode_categorical("Age", "onehot")
    assert "target" not in ENCODE_METHODS


def test_correlation_with_target_and_pairs(tools):
    with_target = json.loads(tools.correlation_analysis(target=SALARY))
    corrs = with_target["correlations"]
    assert corrs and all(-1 <= v <= 1 for v in corrs.values())
    rs = [abs(v) for v in corrs.values()]
    assert rs == sorted(rs, reverse=True)  # strongest first
    pairs = json.loads(tools.correlation_analysis())
    assert pairs["strongest_pairs"] and {"a", "b", "r"} <= set(pairs["strongest_pairs"][0])


def test_correlation_errors(tools):
    with pytest.raises(ValueError, match="is not numeric"):
        tools.correlation_analysis(target="City")


def test_select_top_features_k(tools):
    json.loads(tools.count_items(TECH, ";", "n_techs"))
    result = json.loads(tools.select_top_features(SALARY, k=3))
    assert len(result["kept"]) == 3
    numeric_now = tools.df.select_dtypes(include="number").columns
    assert set(result["kept"]) <= set(numeric_now)
    assert all(c not in tools.df.columns for c in result["dropped"])
    assert SALARY in tools.df.columns  # target survives


def test_select_top_features_threshold_and_errors(tools):
    result = json.loads(tools.select_top_features(SALARY, threshold=0.9))
    assert result["kept"] == []  # nothing correlates that hard in this data
    with pytest.raises(ValueError, match="exactly one"):
        tools.select_top_features(SALARY)
    with pytest.raises(ValueError, match="exactly one"):
        tools.select_top_features(SALARY, k=2, threshold=0.1)


def test_tooldefs_cover_spec(tools):
    defs = {t.name: t for t in tools.tooldefs()}
    assert set(defs) == {"inspect_metadata", "drop_column", "create_interaction",
                         "count_items", "bucketize", "encode_categorical",
                         "correlation_analysis", "select_top_features"}
    assert json.loads(defs["inspect_metadata"].fn())["rows"] == tools.df.shape[0]


def test_save_round_trip(tools, tmp_path):
    tools.count_items(TECH, ";", "n_techs")
    out = tools.save(tmp_path / "eng.csv")
    assert "n_techs" in pd.read_csv(out).columns
