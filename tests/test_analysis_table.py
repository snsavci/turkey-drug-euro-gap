import numpy as np
import pandas as pd
import pytest

import build_analysis_table as bat


def synthetic_market(first: str, last: str, hole: tuple[str, str] | None = None) -> pd.DataFrame:
    """Daily rate 2.0 with empty weekends, shaped like the EVDS download; `hole` empties more days."""
    days = pd.date_range(first, last)
    rates = pd.Series(2.0, index=days).where(days.dayofweek < 5)
    if hole:
        rates[hole[0]:hole[1]] = np.nan
    return pd.DataFrame({"date": days, "market_euro": rates.to_numpy()})


@pytest.fixture(scope="module")
def table() -> pd.DataFrame:
    # needs the real EVDS download, which is git-ignored; the synthetic tests below run without it
    if not list(bat.RAW.glob(bat.MARKET_GLOB)):
        pytest.skip("no EVDS download in data/raw; run src/fetch_evds.py fx first")
    return bat.build_table()


@pytest.fixture(scope="module")
def synthetic_table() -> pd.DataFrame:
    return bat.build_table(synthetic_market("2000-01-01", "2026-12-31"))


def at(table: pd.DataFrame, day: str, column: str) -> float:
    return table.loc[table["date"] == day, column].iloc[0]


def test_dates_are_daily_sorted_and_unique(table):
    assert table["date"].is_unique
    assert table["date"].is_monotonic_increasing
    assert (table["date"].diff().dropna() == pd.Timedelta(days=1)).all()


def test_core_columns_have_no_gaps_or_non_positive_values(table):
    for column in ["drug_euro", "market_euro", "ratio"]:
        assert table[column].notna().all()
        assert (table[column] > 0).all()


def test_units_are_plausible(table):
    assert table["market_euro"].between(0.5, 100).all()
    assert table["drug_euro"].between(0.5, 100).all()
    # the drug euro was above the market rate until 2010, so ratios slightly over 1 are real
    assert table["ratio"].between(0.1, 1.2).all()


def test_drug_euro_changes_only_on_effective_dates(table):
    drug = bat.load_drug_euro()
    changed = table.loc[table["drug_euro"].diff().fillna(0) != 0, "date"]
    assert set(changed) == set(drug["drug_euro_since"].iloc[1:])


def test_drug_euro_matches_source_on_each_effective_date(table):
    drug = bat.load_drug_euro()
    in_table = table.set_index("date").loc[drug["drug_euro_since"], "drug_euro"]
    assert np.allclose(in_table.to_numpy(), drug["drug_euro"].to_numpy())


def test_unpublished_days_carry_the_last_published_rate(table):
    carried = table[~table["rate_published"]]
    previous = table["market_euro"].shift().loc[carried.index]
    assert (carried["market_euro"] == previous).all()


def test_rule_level_is_undefined_before_the_first_coefficient(table):
    first = bat.load_rule_coefficient()["effective_from"].min()
    assert table.loc[table["date"] < first, "rule_level"].isna().all()
    assert table.loc[table["date"] >= first, "rule_level"].notna().all()


@pytest.mark.parametrize(
    "day, decree_value, tolerance",
    [
        # dropping the repeated post-holiday rates from the yearly mean moves these by 6e-4 or more
        ("2016-02-22", 2.1166, 5e-5),
        ("2017-02-20", 2.3421, 5e-5),
        ("2020-02-19", 3.8155, 5e-5),
        ("2022-02-19", 6.2925, 5e-5),
        # Decree 11031 gives these values without the 2025 mean it used, and it bases the mean on
        # the rates announced in the Resmî Gazete, not EVDS; the decree values are 7e-5 and 1e-4 lower
        ("2026-03-13", 26.8767, 1.5e-4),
        ("2026-04-01", 29.1164, 1.5e-4),
    ],
)
def test_rule_level_reproduces_decree_values(table, day, decree_value, tolerance):
    assert at(table, day, "rule_level") == pytest.approx(decree_value, abs=tolerance)


def test_update_window_covers_the_spurious_dip_only(table):
    # the dip that the flag marks: old drug euro against the 2019 level
    assert at(table, "2019-02-13", "update_window")
    assert at(table, "2019-02-13", "compliance") < 0.7
    # the update has come, so the window is closed
    assert not at(table, "2019-02-19", "update_window")
    # a lag in early 2026 is real: the update came only on 13 March
    assert not at(table, "2026-02-10", "update_window")
    assert at(table, "2026-02-10", "compliance") < 1


def test_confidence_is_complete(table):
    assert table["drug_euro_conf"].isin(["A", "B", "C"]).all()


def test_manual_tables_pass_validation():
    # the loaders raise ValueError on bad dates, repeated dates and missing or unknown grades
    assert not bat.load_drug_euro().empty
    assert not bat.load_rule_coefficient().empty


@pytest.mark.parametrize("grade", [None, "D", "a"])
def test_check_confidence_rejects_missing_or_unknown_grades(grade):
    df = pd.DataFrame({"effective_date": pd.to_datetime(["2020-02-19"]), "confidence": [grade]})
    with pytest.raises(ValueError, match="2020-02-19"):
        bat.check_confidence(df, "effective_date", "test.csv")


@pytest.mark.parametrize(
    "day, flagged",
    [
        ("2019-01-01", True),   # before the February 2019 update
        ("2019-02-13", True),
        ("2019-02-19", False),  # the update day itself
        ("2022-02-18", True),
        ("2022-02-19", False),
        ("2025-01-15", False),  # no update early in 2025, so a gap there is real
        ("2026-02-10", False),  # the 2026 update came on 13 March
    ],
)
def test_update_window_ends_on_the_first_update_of_the_year(synthetic_table, day, flagged):
    assert at(synthetic_table, day, "update_window") == flagged


def test_market_euro_is_filled_from_before_the_first_drug_euro_date():
    # the first drug euro date (2007-04-03) falls in a stretch with no published rate
    market = synthetic_market("2007-03-30", "2026-12-31", hole=("2007-04-02", "2007-04-03"))
    table = bat.build_table(market)
    assert table["date"].iloc[0] == pd.Timestamp("2007-04-03")
    assert table["market_euro"].notna().all()
    assert not table["rate_published"].iloc[0]


def test_market_that_starts_after_the_first_drug_euro_date_is_rejected():
    with pytest.raises(ValueError, match="fetch with --start"):
        bat.build_table(synthetic_market("2020-01-01", "2026-12-31"))


def test_check_confidence_names_rows_without_a_date():
    df = pd.DataFrame({"effective_date": pd.to_datetime([None]), "confidence": ["D"]})
    with pytest.raises(ValueError, match="no date"):
        bat.check_confidence(df, "effective_date", "test.csv")


def test_check_dates_names_the_csv_line():
    df = pd.DataFrame({"effective_date": pd.to_datetime(["2020-02-19", None])})
    with pytest.raises(ValueError, match="line.*3"):
        bat.check_dates(df, "effective_date", "test.csv")


@pytest.mark.parametrize("bad_date", ["", "09.07.2022", "2022-13-45"])
def test_loader_rejects_empty_or_unparseable_dates(tmp_path, monkeypatch, bad_date):
    # a text value must not slip through: pandas would otherwise keep the whole column as strings
    (tmp_path / "drug_euro.csv").write_text(
        f"effective_date,value_try,confidence\n2020-02-19,3.8155,A\n{bad_date},4.5786,A\n", encoding="utf-8"
    )
    monkeypatch.setattr(bat, "MANUAL", tmp_path)
    with pytest.raises(ValueError, match="line.*3"):
        bat.load_drug_euro()


def test_check_unique_dates_names_the_repeated_date():
    df = pd.DataFrame({"effective_date": pd.to_datetime(["2020-02-19", "2021-02-20", "2020-02-19"])})
    with pytest.raises(ValueError, match="2020-02-19"):
        bat.check_unique_dates(df, "effective_date", "test.csv")


def write_market_file(folder, name, rows):
    pd.DataFrame(rows, columns=["Tarih", "TP_DK_EUR_S_YTL"]).to_csv(folder / name, index=False)


def test_overlapping_downloads_are_merged_and_the_later_file_wins(tmp_path, monkeypatch):
    write_market_file(tmp_path, "evds_eur_daily_2026-11-03.csv", [("01-02-2020", 6.0), ("03-02-2020", 6.1)])
    write_market_file(
        tmp_path, "evds_eur_daily_2026-11-03_2020-02-03_2020-02-04.csv", [("03-02-2020", 6.2), ("04-02-2020", 6.3)]
    )
    monkeypatch.setattr(bat, "RAW", tmp_path)
    market = bat.load_market_euro()
    assert market["date"].dt.strftime("%Y-%m-%d").tolist() == ["2020-02-01", "2020-02-03", "2020-02-04"]
    assert market["market_euro"].tolist() == [6.0, 6.2, 6.3]


def test_missing_market_download_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(bat, "RAW", tmp_path)
    with pytest.raises(FileNotFoundError, match="fetch_evds.py fx"):
        bat.market_files()


def test_ratio_matches_ieis_august_2026_report(table):
    assert at(table, "2026-08-31", "ratio") == pytest.approx(0.519, abs=0.001)
