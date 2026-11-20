from datetime import date

import httpx
import pytest

from marketlens.config import get_settings
from marketlens.providers.base import ProviderError, ProviderNotConfigured
from marketlens.providers.edgar import EdgarProvider
from marketlens.providers.finnhub import FinnhubProvider
from marketlens.providers.fred import FredCsvProvider
from marketlens.providers.http import ApiClient
from marketlens.providers.twelvedata import TwelveDataProvider

FAKE_KEY = "test-key-should-never-leak"


@pytest.fixture(autouse=True)
def fake_env(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", FAKE_KEY)
    monkeypatch.setenv("TWELVE_DATA_API_KEY", FAKE_KEY)
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "Test Agent test@example.com")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _fast(provider):
    provider.client.limiter.interval = 0
    provider.client._backoff = 0
    return provider


def test_finnhub_news_one_call_per_day_and_dedup():
    seen = []

    def handler(req: httpx.Request):
        seen.append(dict(req.url.params))
        assert req.headers["X-Finnhub-Token"] == FAKE_KEY
        assert FAKE_KEY not in str(req.url)  # key only ever in headers
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "datetime": 1763600000,
                    "headline": "Nvidia beats",
                    "summary": "s",
                    "source": "Reuters",
                    "url": "https://x.test/a",
                    "related": "NVDA,AMD",
                },
                {"id": 2, "datetime": 1763600000, "headline": "", "url": "https://x.test/b"},
            ],
        )

    p = _fast(FinnhubProvider(transport=httpx.MockTransport(handler)))
    items = p.company_news("NVDA", date(2026, 11, 18), date(2026, 11, 20))
    assert len(seen) == 3 and seen[0]["from"] == seen[0]["to"] == "2026-11-18"
    assert len(items) == 1  # same id deduped across days; empty headline dropped
    assert items[0].related_tickers == ("NVDA", "AMD")
    assert items[0].published_at.tzinfo is not None


def test_finnhub_profile_market_cap_in_usd():
    t = httpx.MockTransport(
        lambda r: httpx.Response(
            200, json={"name": "NVIDIA Corp", "marketCapitalization": 3_500_000.0}
        )
    )
    prof = _fast(FinnhubProvider(transport=t)).profile("NVDA")
    assert prof.market_cap_usd == pytest.approx(3.5e12)


def test_retries_then_succeeds_on_429():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(429) if calls["n"] < 3 else httpx.Response(200, json=[])

    p = _fast(FinnhubProvider(transport=httpx.MockTransport(handler)))
    assert p.company_news("NVDA", date(2026, 1, 1), date(2026, 1, 1)) == []
    assert calls["n"] == 3


def test_gives_up_without_leaking_key():
    c = ApiClient(
        "x",
        "https://x.test",
        1e9,
        headers={"Authorization": FAKE_KEY},
        transport=httpx.MockTransport(lambda r: httpx.Response(503)),
        max_attempts=2,
        backoff_initial=0,
    )
    with pytest.raises(ProviderError) as exc:
        c.get("/y")
    assert FAKE_KEY not in str(exc.value)


def test_twelvedata_parses_and_reports_error_body():
    def handler(req):
        assert req.headers["Authorization"] == f"apikey {FAKE_KEY}"
        if req.url.params["symbol"] == "BAD":
            return httpx.Response(200, json={"status": "error", "code": 400, "message": "nope"})
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "values": [
                    {
                        "datetime": "2026-11-18",
                        "open": "1",
                        "high": "2",
                        "low": "0.5",
                        "close": "1.5",
                        "volume": "100",
                    },
                    {
                        "datetime": "2026-11-17",
                        "open": "1",
                        "high": "2",
                        "low": "0.5",
                        "close": "1.2",
                        "volume": "90",
                    },
                ],
            },
        )

    p = _fast(TwelveDataProvider(transport=httpx.MockTransport(handler)))
    df = p.daily_bars("NVDA", date(2026, 11, 1), date(2026, 11, 20))
    assert list(df.trade_date) == [date(2026, 11, 17), date(2026, 11, 18)]
    assert df.volume.dtype == "int64"
    with pytest.raises(ProviderError, match="400"):
        p.daily_bars("BAD", date(2026, 11, 1), date(2026, 11, 20))


def test_edgar_requires_user_agent(monkeypatch):
    monkeypatch.delenv("SEC_EDGAR_USER_AGENT")
    get_settings.cache_clear()
    with pytest.raises(ProviderNotConfigured):
        EdgarProvider()


def test_edgar_filters_forms_and_builds_urls():
    body = {
        "filings": {
            "recent": {
                "form": ["8-K", "4", "10-Q", "8-K"],
                "filingDate": ["2026-11-10", "2026-11-09", "2026-10-30", "2025-01-01"],
                "reportDate": ["2026-11-07", "", "2026-09-30", ""],
                "accessionNumber": ["0001-26-1", "0001-26-2", "0001-26-3", "0001-25-4"],
                "primaryDocument": ["a.htm", "b.xml", "c.htm", "d.htm"],
            }
        }
    }
    t = httpx.MockTransport(lambda r: httpx.Response(200, json=body))
    out = _fast(EdgarProvider(transport=t)).recent_filings(
        "0001045810", ("8-K", "10-Q", "10-K"), date(2026, 1, 1)
    )
    assert [f.form for f in out] == ["8-K", "10-Q"]
    assert out[0].url == "https://www.sec.gov/Archives/edgar/data/1045810/0001261/a.htm"


def test_fred_csv_handles_missing_values():
    csv = "observation_date,DGS10\n2026-11-14,.\n2026-11-17,5.10\n"
    t = httpx.MockTransport(lambda r: httpx.Response(200, text=csv))
    df = _fast(FredCsvProvider(transport=t)).series("DGS10", date(2026, 11, 1))
    assert df["value"].isna().tolist() == [True, False]
    assert df["obs_date"].iloc[1] == date(2026, 11, 17)


def test_finnhub_not_configured(monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY")
    get_settings.cache_clear()
    with pytest.raises(ProviderNotConfigured):
        FinnhubProvider()
