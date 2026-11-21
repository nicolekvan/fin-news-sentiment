from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text

from marketlens.api import app as app_module
from marketlens.api.deps import read_engine, write_engine
from marketlens.config import get_settings
from marketlens.db.repository import upsert_companies, upsert_prices
from marketlens.demo import DEMO_SOURCE, demo_news, demo_prices
from marketlens.jobs import aggregate as agg_job
from marketlens.jobs import indicators as ind_job
from marketlens.jobs import news as news_job
from marketlens.universe import load_universe
from tests.test_news_job import FakeFinBert


@pytest.fixture(scope="module")
def seeded(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "truncate companies, news_articles, model_versions, llm_usage, "
                "ingestion_logs restart identity cascade"
            )
        )
        companies = load_universe(dev_only=True)
        ids = upsert_companies(conn, companies)
        for c in companies:
            upsert_prices(conn, ids[c.ticker], demo_prices(c.ticker), DEMO_SOURCE)
    ind_job.run(engine)
    raw = []
    for c in companies:
        if c.is_benchmark:
            continue
        df = demo_news(c.ticker, c.aliases[0])
        for r in df.itertuples():
            raw.append(
                {
                    "provider": "demo",
                    "provider_article_id": r.provider_article_id,
                    "url": r.url,
                    "headline": r.headline,
                    "summary": r.summary,
                    "source_name": r.source_name,
                    "published_at": r.published_at.isoformat(),
                    "related_tickers": [],
                }
            )
    news_job.run(date(2026, 11, 20), engine=engine, model=FakeFinBert(), raw=raw)
    agg_job.run(engine)
    yield engine
    with engine.begin() as conn:  # leave the database empty for other test modules
        conn.execute(
            text(
                "truncate companies, news_articles, model_versions, llm_usage, "
                "ingestion_logs restart identity cascade"
            )
        )


@pytest.fixture(scope="module")
def client(seeded, engine):
    reader = create_engine(engine.url)

    @event.listens_for(reader, "connect")
    def _as_reader(dbapi_conn, _):
        with dbapi_conn.cursor() as cur:
            cur.execute("set role marketlens_reader")
        dbapi_conn.commit()

    app_module.app.dependency_overrides[read_engine] = lambda: reader
    app_module.app.dependency_overrides[write_engine] = lambda: engine
    with TestClient(app_module.app, raise_server_exceptions=False) as c:
        yield c
    app_module.app.dependency_overrides.clear()


def test_health_and_meta(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    m = client.get("/api/meta").json()
    assert m["has_demo_prices"] is True and "not investment advice" in m["disclaimer"]
    assert m["aggregation"]["method_version"] == "agg-v1"


def test_screener_covers_all_companies(client):
    rows = client.get("/api/companies").json()
    assert len(rows) == 12
    nvda = next(r for r in rows if r["ticker"] == "NVDA")
    assert nvda["close"] is not None and nvda["rsi_14"] is not None
    assert nvda["sentiment_label"] in ("bullish", "bearish", "neutral", "insufficient_evidence")


def test_company_detail_and_benchmark_relative(client):
    r = client.get("/api/companies/NVDA").json()
    assert r["benchmark"] == "QQQ" and "vs_qqq_3m" in r
    assert client.get("/api/companies/NOPE").status_code == 404
    assert client.get("/api/companies/drop table").status_code == 422


def test_prices_with_indicators_and_range_validation(client):
    rows = client.get(
        "/api/companies/AAPL/prices", params={"start": "2026-06-01", "end": "2026-11-20"}
    ).json()
    assert rows and {"close", "sma_50", "bb_upper", "atr_14"} <= set(rows[0])
    bad = client.get(
        "/api/companies/AAPL/prices", params={"start": "2020-01-01", "end": "2026-11-20"}
    )
    assert bad.status_code == 422


def test_news_filters_and_links(client):
    rows = client.get("/api/news", params={"ticker": "AMD", "limit": 5}).json()
    assert 0 < len(rows) <= 5
    assert all(r["ticker"] == "AMD" and r["url"].startswith("https://") for r in rows)
    assert all(r["explanation"] and r["source_name"] for r in rows)
    bull = client.get("/api/news", params={"label": "bullish"}).json()
    assert all(r["label"] == "bullish" for r in bull)
    assert client.get("/api/news", params={"limit": 1000}).status_code == 422
    assert client.get("/api/news", params={"label": "moon"}).status_code == 422
    # LIKE wildcards in search are escaped, not interpreted
    assert client.get("/api/news", params={"q": "%"}).json() == []


def test_sentiment_history_and_events(client):
    hist = client.get("/api/companies/MSFT/sentiment").json()
    assert hist and all(-1 <= h["score"] <= 1 for h in hist)
    ev = client.get("/api/companies/MSFT/events").json()
    assert set(ev) == {"news", "filings"}


def test_overview_shape(client):
    o = client.get("/api/overview").json()
    assert set(o["counts"]) == {"bullish", "bearish", "neutral", "insufficient_evidence"}
    assert sum(o["counts"].values()) == 10
    assert len(o["heatmap"]) == 10 and len(o["top_gainers"]) == 5


def test_admin_disabled_without_token(client, monkeypatch):
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    get_settings.cache_clear()
    assert client.post("/api/admin/aggregate").status_code == 404


def test_admin_requires_correct_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "correct-horse")
    get_settings.cache_clear()
    assert client.post("/api/admin/aggregate").status_code == 401
    assert (
        client.post("/api/admin/aggregate", headers={"Authorization": "Bearer wrong"}).status_code
        == 401
    )
    ok = client.post("/api/admin/aggregate", headers={"Authorization": "Bearer correct-horse"})
    assert ok.status_code == 200 and ok.json()["rows"] > 0
    get_settings.cache_clear()


def test_rate_limit(client):
    statuses = [client.get("/api/macro").status_code for _ in range(130)]
    assert 429 in statuses


def test_overview_counts_companies_without_scores(client, engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "insert into companies (ticker, name, industry, cik) "
                "values ('ZZZ', 'No News Co', 'Software & Cloud', '0009999999')"
            )
        )
    try:
        o = client.get("/api/overview").json()
        assert sum(o["counts"].values()) == 11
        assert o["counts"]["insufficient_evidence"] >= 1
    finally:
        with engine.begin() as conn:
            conn.execute(text("delete from companies where ticker = 'ZZZ'"))
