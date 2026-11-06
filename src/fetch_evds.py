"""Download CBRT EVDS series into data/raw/.

Usage (from the repository root):
    python src/fetch_evds.py fx --start 2000-01-01 --end 2026-10-30
    python src/fetch_evds.py prices --start 2000-01-01 --end 2026-10-30
"""
import argparse
from datetime import date
from pathlib import Path

import pandas as pd
from evds import evdsAPI

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER_KEY = "your_key_here"  # the value in .env.example

DATASETS = {
    # daily euro rates: selling, buying
    "fx": {
        "series": ["TP.DK.EUR.S.YTL", "TP.DK.EUR.A.YTL"],
        "frequency": None,
        "chunk_years": 1,  # one request per year keeps daily pulls well inside API limits
        "file": "evds_eur_daily",
    },
    # monthly price indices
    "prices": {
        "series": [
            "TP.TUKFIY2025.GENEL",  # CPI, 2025=100, available from 2005
            "TP.TUKFIY2025.061",  # CPI: medicines and health products, 2025=100
            "TP.TUKFIY2025.0611",  # CPI: medicines, 2025=100
            "TP.GENENDEKS.T1",  # CPI, 2003=100 (old base, available from 2003)
            "TP.TUFE1YI.T1",  # domestic PPI, general
            "TP.TUFE1YI.T59",  # domestic PPI: basic pharmaceutical products (NACE 21)
            "TP.TUFE1YI.T60",  # domestic PPI: pharmaceutical preparations
        ],
        "frequency": 5,  # monthly
        "chunk_years": None,  # whole range in one request
        "file": "evds_prices_monthly",
    },
}


def read_api_key() -> str:
    env_file = ROOT / ".env"
    if not env_file.exists():
        raise SystemExit("no .env file; copy .env.example to .env and put your EVDS key in it")
    # utf-8-sig drops the BOM that Notepad and PowerShell add to the first line
    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("EVDS_API_KEY="):
            key = line.split("=", 1)[1].strip().strip("\"'")
            if key and key != PLACEHOLDER_KEY:
                return key
    raise SystemExit("EVDS_API_KEY is missing, empty or still the placeholder in .env")


def fetch(dataset: dict, start: date, end: date) -> pd.DataFrame:
    evds = evdsAPI(read_api_key())
    kwargs = {}
    if dataset["frequency"]:
        kwargs["frequency"] = dataset["frequency"]
    frames = []
    step = dataset["chunk_years"] or end.year - start.year + 1
    for year in range(start.year, end.year + 1, step):
        chunk_start = max(start, date(year, 1, 1))
        chunk_end = min(end, date(year + step - 1, 12, 31))
        df = evds.get_data(
            dataset["series"],
            startdate=chunk_start.strftime("%d-%m-%Y"),
            enddate=chunk_end.strftime("%d-%m-%Y"),
            **kwargs,
        )
        print(f"{chunk_start.year}-{chunk_end.year}: {len(df)} rows")
        # a wrong key or an exhausted quota can come back as an empty frame
        if df.empty:
            raise SystemExit(f"EVDS returned no rows for {chunk_start} to {chunk_end}; nothing was saved")
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", choices=DATASETS)
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--start must not be after --end")

    dataset = DATASETS[args.dataset]
    df = fetch(dataset, args.start, args.end)
    # the range is in the name, so a second fetch on the same day with other dates keeps the first file
    out = ROOT / "data" / "raw" / f"{dataset['file']}_{date.today()}_{args.start}_{args.end}.csv"
    df.to_csv(out, index=False)
    print(f"saved {len(df)} rows to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
