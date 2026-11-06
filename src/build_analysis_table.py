"""Build data/processed/analysis_table.csv: one row per day with the drug euro,
the market euro, their ratio and the rule level.

Usage (from the repository root, after running fetch_evds.py fx):
    python src/build_analysis_table.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MANUAL = ROOT / "data" / "manual"
OUT = ROOT / "data" / "processed" / "analysis_table.csv"
MARKET_GLOB = "evds_eur_daily_*.csv"


def market_files() -> list[Path]:
    files = sorted(RAW.glob(MARKET_GLOB))  # by name: download date, then start date
    if not files:
        raise FileNotFoundError(
            f"no {MARKET_GLOB} in data/raw; run: python src/fetch_evds.py fx --start 2000-01-01 --end <date>"
        )
    return files


def check_dates(df: pd.DataFrame, key: str, source: str) -> None:
    missing = df.index[df[key].isna()]
    if len(missing):
        lines = ", ".join(str(i + 2) for i in missing)  # +2: header line, then 1-based
        raise ValueError(f"{source}: {key} is empty or not a date on line(s) {lines}")


def check_unique_dates(df: pd.DataFrame, key: str, source: str) -> None:
    repeated = df.loc[df[key].duplicated(keep=False), key]
    if not repeated.empty:
        days = ", ".join(repeated.dt.strftime("%Y-%m-%d").unique())
        raise ValueError(f"{source}: {key} is repeated for {days}")


def check_confidence(df: pd.DataFrame, key: str, source: str) -> None:
    bad = df.loc[~df["confidence"].isin(["A", "B", "C"]), key]
    if not bad.empty:
        days = ", ".join(bad.dt.strftime("%Y-%m-%d").fillna("no date"))
        raise ValueError(f"{source}: confidence must be A, B or C; check rows dated {days}")


def load_market_euro() -> pd.DataFrame:
    # all downloads are merged, so a narrow or repeated fetch cannot replace the full history;
    # where files overlap, the one that sorts last by name wins
    frames = [pd.read_csv(path) for path in market_files()]
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["Tarih"], format="%d-%m-%Y")
    df = df.rename(columns={"TP_DK_EUR_S_YTL": "market_euro"})[["date", "market_euro"]]
    return df.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


def load_drug_euro() -> pd.DataFrame:
    df = pd.read_csv(MANUAL / "drug_euro.csv")
    df["effective_date"] = pd.to_datetime(df["effective_date"], format="%Y-%m-%d", errors="coerce")
    check_dates(df, "effective_date", "drug_euro.csv")
    check_unique_dates(df, "effective_date", "drug_euro.csv")
    check_confidence(df, "effective_date", "drug_euro.csv")
    df = df.rename(
        columns={"value_try": "drug_euro", "effective_date": "drug_euro_since", "confidence": "drug_euro_conf"}
    )
    return df[["drug_euro_since", "drug_euro", "drug_euro_conf"]].sort_values("drug_euro_since")


def load_rule_coefficient() -> pd.DataFrame:
    df = pd.read_csv(MANUAL / "rule_coefficient.csv")
    df["effective_from"] = pd.to_datetime(df["effective_from"], format="%Y-%m-%d", errors="coerce")
    check_dates(df, "effective_from", "rule_coefficient.csv")
    check_unique_dates(df, "effective_from", "rule_coefficient.csv")
    check_confidence(df, "effective_from", "rule_coefficient.csv")
    return df[["effective_from", "coefficient"]].sort_values("effective_from")


def update_window(dates: pd.Series, drug: pd.DataFrame) -> pd.Series:
    """True from 1 January until the drug euro update of that year, in years whose first update
    came in January or February. In these days the rule level already belongs to the new year
    while the drug euro still holds the old value, so compliance below 1 is not a real lag."""
    since = drug["drug_euro_since"]
    first = since.groupby(since.dt.year).min()
    first = first[first.dt.month <= 2]
    return dates < dates.dt.year.map(first)  # years without an early update map to NaT: False


def build_table(market: pd.DataFrame | None = None) -> pd.DataFrame:
    market = load_market_euro() if market is None else market
    drug = load_drug_euro()
    coefficient = load_rule_coefficient()

    first_day, last_day = drug["drug_euro_since"].min(), market["date"].max()
    if market["date"].min() > first_day:
        raise ValueError(
            f"market euro starts {market['date'].min().date()}, after the first drug euro date "
            f"{first_day.date()}; fetch with --start 2000-01-01"
        )

    # EVDS leaves weekends and holidays empty, so the yearly mean must skip them. It repeats the
    # previous rate on some days after holidays; those stay in, because only then do the means
    # reproduce the decree values to four decimals
    published = market.dropna(subset=["market_euro"])
    yearly_mean = published.groupby(published["date"].dt.year)["market_euro"].mean()

    # fill over the whole market series first, so days before the first published rate still get one
    filled = market.set_index("date")["market_euro"].asfreq("D").ffill()
    table = pd.DataFrame({"date": pd.date_range(first_day, last_day)})
    table["market_euro"] = table["date"].map(filled)
    table["rate_published"] = table["date"].isin(published["date"])
    table = pd.merge_asof(table, drug, left_on="date", right_on="drug_euro_since")
    table = pd.merge_asof(table, coefficient, left_on="date", right_on="effective_from")
    table = table.drop(columns="effective_from")

    table["ratio"] = table["drug_euro"] / table["market_euro"]
    table["gap"] = 1 - table["ratio"]
    # rule level of the calendar year, so Jan-Feb rows compare the old value to the new year's level
    previous_mean = (table["date"].dt.year - 1).map(yearly_mean)
    table["rule_level"] = table["coefficient"] * previous_mean
    table["compliance"] = table["drug_euro"] / table["rule_level"]
    table["update_window"] = update_window(table["date"], drug)

    return table[
        ["date", "drug_euro", "drug_euro_since", "drug_euro_conf", "market_euro", "rate_published",
         "ratio", "gap", "coefficient", "rule_level", "compliance", "update_window"]
    ]


def main() -> None:
    try:
        print("market euro from " + ", ".join(str(p.relative_to(ROOT)) for p in market_files()))
        table = build_table()
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(f"error: {error}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False)
    first, last = table["date"].min().date(), table["date"].max().date()
    print(f"saved {len(table)} rows ({first} to {last}) to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
