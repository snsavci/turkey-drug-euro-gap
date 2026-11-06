# Turkey's Drug Euro Gap

Turkey prices medicines with a government-set exchange rate, the **drug euro**, that has fallen far behind the market euro. This project measures how that gap has evolved, checks whether the government's own indexation rule is being followed, and tests whether the gap is linked to medicine shortages.

| | Drug euro | Market euro | Ratio |
|---|---|---|---|
| 31 Aug 2026 | 29.1164 TL | 56.0853 TL | 51.9% |

*Drug euro in force since 1 April 2026 (IEIS, August 2026 report). Market euro is the end-of-month rate used in that report.*

**Status:** the drug euro table, the EVDS downloads and the daily analysis table are done; the shortage indicators, the analysis, the dashboard and the write-up are not started, so there are no findings yet.

| Stage | State |
|---|---|
| Drug euro table (`data/manual/drug_euro.csv`) | 21 changes from April 2007 to April 2026. Each row has a source link and a confidence grade in the `confidence` column: A (decree text read, 9 rows), B (value reproduced from the rule, 6 rows), C (value and date only from a secondary table, 6 rows; all from 2007-2015) |
| Rule coefficient history (`rule_coefficient.csv`) | Done: 0.70 from 2016, 0.60 from 2019, 0.65 from April 2026 |
| Market euro and price indices (EVDS) | Downloaded to `data/raw/` on 3 November 2026 |
| Daily analysis table | Built: 7,151 days from 3 April 2007 to 30 October 2026; 46 tests pass |
| Shortage indicators (Google Trends, `events.csv`) | Not started |
| Inflation comparison, update-by-update measures, charts | Not started |
| Dashboard and write-up | Not started |

## Background: how a medicine price is set

For most medicines sold in Turkey, the price is built in four steps:

1. **Reference price.** Take the lowest ex-factory price of the medicine in France, Spain, Italy, Portugal and Greece, in euros.
2. **Conversion.** Multiply by the drug euro (officially the *dönemsel avro değeri*, "periodic euro value") to get a price in TL.
3. **Drug euro level.** By rule, the drug euro is the previous year's average CBRT daily euro selling rate multiplied by an adaptation coefficient `k`. The coefficient was raised from 0.60 to 0.65 in April 2026.
4. **Retail price.** Wholesaler and pharmacist margins are added.

Written as a formula, with `D_t` the drug euro, `S` the CBRT euro selling rate and `N` the number of days in the previous year on which a rate was published:

$$D_t = k \times \frac{1}{N} \sum_{g=1}^{N} S_{g,\,t-1}$$

In recent years the drug euro was changed by decision one to three times a year (three times in 2022), so in a year of fast depreciation it can sit far below the market rate for months.

## Research questions

**Core**

1. How has the ratio of the drug euro to the market euro changed over time, and when did the gap widen most?
2. How closely do actual updates follow the rule above?
3. How much does the gap close after each update, and how long until it reopens?

**Extended**

4. Do searches and news about medicine shortages increase when the gap widens?
5. How far have medicine prices fallen behind general inflation?

## Measures

| Symbol | Name | Definition |
|---|---|---|
| `D_t` | Drug euro | Value in force on day `t` (effective date, not publication date) |
| `P_t` | Market euro | CBRT daily euro selling rate, `TP.DK.EUR.S.YTL` |
| `R_t` | Ratio | `D_t / P_t` |
| `F_t` | Gap | `1 − R_t` |
| `K_t` | Rule level | `k ×` previous year's mean of `P`, over days with a published rate |
| `U_t` | Rule compliance | `D_t / K_t`; below 1 means the drug euro lags its own rule. `K_t` switches on 1 January, but in years when the first drug euro update came in January or February (2016 to 2022) `U_t` is below 1 from 1 January until that update without a real lag. Those days carry `update_window = True` in the analysis table; from 2023 on the updates came later in the year, so a gap in January and February is a real lag |

Also computed per update: the **jump** in the ratio, and the **decay time** until the ratio falls back to its pre-update level. For the inflation comparison: the drug euro deflated by CPI, and the drug euro, CPI and pharmaceutical PPI indexed to 100 at a common start date.

## Data sources

| Data | Source | Notes |
|---|---|---|
| Drug euro values and dates | Official Gazette (*Resmî Gazete*) pricing decrees, compiled by hand: 11 of the 21 rows link to one. The other 10 rest on secondary sources: the TEİS table (8 rows), a law-firm article (1) and a news article (1) | Each row carries a source link and a confidence grade that says how far the value and date were checked. News tables are used only as a starting point |
| Market euro, daily | CBRT EVDS (`TP.DK.EUR.S.YTL`, buying rate `TP.DK.EUR.A.YTL`) | Needs a free EVDS API key |
| Inflation | EVDS / TURKSTAT: CPI (`TP.TUKFIY2025.GENEL`), CPI for medicines (`TP.TUKFIY2025.0611`), domestic PPI (`TP.TUFE1YI.T1`), pharmaceutical PPI, NACE 21 (`TP.TUFE1YI.T59`) | CPI moved to a 2025=100 base in January 2026. EVDS serves the 2025=100 series back to 2005, and the old 2003=100 series is the same data rescaled, so no chaining is needed |
| Cross-check | IEIS monthly *Price and Exchange Rate Developments* report | Uses the end-of-month rate, which gives slightly different ratios than the formula |
| Shortage interest (extended scope) | Google Trends | Relative 0-100 index, rescaled on every download |
| Shortage claims (extended scope) | Hand-kept event list from pharmacists' associations, regulators and parliamentary questions | Methods behind the figures are often unclear |

## Repository layout

| Path | Contents |
|---|---|
| `data/raw/` | Downloaded files, left untouched and not tracked by git |
| `data/manual/` | Hand-compiled tables: `drug_euro.csv` (one row per drug euro change), `rule_coefficient.csv` (the coefficient `k` over time) and `events.csv` (shortage statements and rule changes) |
| `data/processed/` | Cleaned, merged tables used for analysis |
| `notebooks/` | Collection, cleaning and analysis notebooks |
| `src/` | Reusable Python code |
| `app/` | Streamlit dashboard |
| `reports/figures/` | Exported charts |
| `docs/` | Glossary |

## Known pitfalls

- **Publication vs effective date.** An update can be published a day or more before it takes effect. The analysis uses the effective date.
- **Which euro rate.** The legal formula uses the average daily selling rate of the previous year. IEIS reports the end-of-month rate. Every chart states which one it uses.
- **Repeated EVDS rates.** On 73 days since 2000 (mostly the first day after a holiday) EVDS carries the same selling rate as the previous published day. `rate_published` means that EVDS has a value for the day, not that the CBRT announced a new rate. These days stay in the yearly mean, because removing them stops the means from reproducing the decree values to four decimals.
- **Not every medicine follows the rule.** Some groups, such as orphan drugs, biosimilars and vaccines, have flexible pricing, and wholesaler and pharmacist margins vary by price band. The gap describes the rule-based pricing, not all medicine prices.
- **Shortages are not directly measured.** There is no official shortage series. Search interest and association statements are indirect indicators, and any link found is a correlation, not proof of cause. Shortages also have other drivers, including global raw-material problems and distribution imbalances.
- **Official wording.** A new communiqué from 29 August 2026 also defines a "current euro value" based on the CBRT rate published every two weeks. Until it is clear which products it applies to, the analysis is limited to the periodic euro value.

## Running the project

Requires Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Store the EVDS API key in a `.env` file at the repository root (git-ignored):

```
EVDS_API_KEY=your_key_here
```

Then download the EVDS series, build the analysis table and run the tests:

```bash
python src/fetch_evds.py fx --start 2000-01-01 --end 2026-10-30
python src/fetch_evds.py prices --start 2000-01-01 --end 2026-10-30
python src/build_analysis_table.py
python -m pytest tests
```

## Data and sources

`data/manual/drug_euro.csv` and `rule_coefficient.csv` carry a source link for every row; check the confidence grade before relying on a value. Raw EVDS downloads are not tracked by git: rebuild them with the commands above. A data dictionary and a public release of the dataset are planned. Third-party reports are cited, not redistributed.
