"""Fingerprint check for the committed official dataset (u02).

Confirms data/IT_Salary_Survey_EU_2020.csv is the right file: exact shape plus
the known dirt markers the agents are expected to discover and handle. This is
a *data* check, not harness code — naming dataset columns here is fine
(NO-HARDCODE scopes to harness source; the u17 grep excludes tests/ and data/).
"""

from pathlib import Path

import pandas as pd
import pytest

CSV = Path(__file__).resolve().parent.parent / "data" / "IT_Salary_Survey_EU_2020.csv"


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return pd.read_csv(CSV)


def test_shape(df):
    assert df.shape == (1246, 23)


def test_trailing_space_column(df):
    assert "Position " in df.columns  # trailing space — real dirt, do not strip


def test_cyrillic_contract_duration_column(df):
    matches = [c for c in df.columns if "ontract duration" in c]
    assert len(matches) == 1
    first = matches[0][0]
    assert first == "С", f"expected Cyrillic С (U+0421), got {first!r} (U+{ord(first):04X})"
    assert first != "C"  # not ASCII


def test_missing_heavy_skip_logic_columns(df):
    missing_frac = df.isna().mean()
    kurzarbeit = [c for c in df.columns if "Kurzarbeit" in c]
    assert len(kurzarbeit) == 1
    assert missing_frac[kurzarbeit[0]] > 0.6  # ≈70 % missing
    # at least one other column (WFH/stock-related skip logic) >60 % missing
    heavy = missing_frac[missing_frac > 0.6]
    assert len(heavy) >= 2


def test_salary_outlier_present(df):
    yearly = [c for c in df.columns if c.startswith("Yearly brutto salary")]
    assert yearly, f"no yearly salary column found in {list(df.columns)}"
    col = pd.to_numeric(df[yearly[0]], errors="coerce")
    assert col.max() >= 1e8  # the famous €1e11 / €500M junk rows


def test_noisy_categories_present(df):
    # 23-distinct-value Seniority level — category normalization bait
    assert df["Seniority level"].nunique() > 15
