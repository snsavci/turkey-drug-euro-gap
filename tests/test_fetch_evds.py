from datetime import date

import pandas as pd
import pytest

import fetch_evds as fe


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    monkeypatch.setattr(fe, "ROOT", tmp_path)
    return tmp_path / ".env"


@pytest.fixture
def requests_made(monkeypatch):
    made = []

    class FakeEvds:
        def __init__(self, key):
            pass

        def get_data(self, series, startdate, enddate, **kwargs):
            made.append((startdate, enddate, kwargs))
            return pd.DataFrame({"Tarih": [startdate]})

    monkeypatch.setattr(fe, "evdsAPI", FakeEvds)
    monkeypatch.setattr(fe, "read_api_key", lambda: "key")
    return made


def test_read_api_key_handles_a_bom_and_quotes(env_file):
    env_file.write_text('EVDS_API_KEY= "abc123" \n', encoding="utf-8-sig")
    assert fe.read_api_key() == "abc123"


@pytest.mark.parametrize("content", ["", "OTHER=1\n", "EVDS_API_KEY=\n", "EVDS_API_KEY=your_key_here\n"])
def test_read_api_key_rejects_missing_empty_or_placeholder_keys(env_file, content):
    env_file.write_text(content, encoding="utf-8")
    with pytest.raises(SystemExit, match="EVDS_API_KEY"):
        fe.read_api_key()


def test_read_api_key_needs_the_env_file(env_file):
    with pytest.raises(SystemExit, match=r"\.env"):
        fe.read_api_key()


def test_daily_fetch_makes_one_request_per_calendar_year(requests_made):
    fe.fetch(fe.DATASETS["fx"], date(2019, 6, 15), date(2021, 3, 1))
    assert [made[:2] for made in requests_made] == [
        ("15-06-2019", "31-12-2019"),
        ("01-01-2020", "31-12-2020"),
        ("01-01-2021", "01-03-2021"),
    ]


def test_monthly_fetch_makes_one_request_for_the_whole_range(requests_made):
    fe.fetch(fe.DATASETS["prices"], date(2000, 1, 1), date(2026, 10, 30))
    assert requests_made == [("01-01-2000", "30-10-2026", {"frequency": 5})]


def test_empty_response_stops_the_fetch(monkeypatch):
    class EmptyEvds:
        def __init__(self, key):
            pass

        def get_data(self, *args, **kwargs):
            return pd.DataFrame()

    monkeypatch.setattr(fe, "evdsAPI", EmptyEvds)
    monkeypatch.setattr(fe, "read_api_key", lambda: "key")
    with pytest.raises(SystemExit, match="nothing was saved"):
        fe.fetch(fe.DATASETS["fx"], date(2020, 1, 1), date(2020, 12, 31))
