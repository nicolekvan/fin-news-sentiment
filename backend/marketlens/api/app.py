"""MarketLens read API.

uvicorn marketlens.api.app:app
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import Engine, text

from marketlens.aggregate import CONFIG as AGG_CONFIG
from marketlens.aggregate import METHOD_VERSION as AGG_VERSION
from marketlens.api import queries as q
from marketlens.api.deps import read_engine, require_admin, write_engine
from marketlens.config import get_settings

log = logging.getLogger("marketlens.api")
DISCLAIMER = (
    "MarketLens AI is an educational portfolio project. Sentiment labels describe the "
    "tone of news coverage and are not investment advice or price predictions."
)
TickerPath = Path(pattern=r"^[A-Z.]{1,10}$")
Label = Literal["bullish", "bearish", "neutral", "insufficient_evidence"]

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
app = FastAPI(
    title="MarketLens AI API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)  # applies default_limits to every route
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["GET"])


@app.exception_handler(Exception)
async def generic_error(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled error on %s: %s", request.url.path, type(exc).__name__)
    return JSONResponse({"detail": "Internal error"}, status_code=500)  # no internals leaked


def _rows(engine: Engine, sql: str, **params) -> list[dict]:
    with engine.connect() as conn:
        return [
            {k: float(v) if isinstance(v, Decimal) else v for k, v in r._mapping.items()}
            for r in conn.execute(text(sql), params)
        ]


def _company_id(engine: Engine, ticker: str) -> int:
    rows = _rows(engine, "select id from companies where ticker = :t", t=ticker)
    if not rows:
        raise HTTPException(404, "Unknown ticker")
    return rows[0]["id"]


@app.get("/api/health")
@limiter.exempt
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/meta")
def meta(request: Request, engine: Engine = Depends(read_engine)) -> dict:
    r = _rows(
        engine,
        """
        select (select max(trade_date) from stock_prices) as prices_as_of,
               (select max(published_at) from news_articles) as news_as_of,
               greatest((select max(ingested_at) from stock_prices),
                        (select max(ingested_at) from news_articles)) as last_ingested_at,
               (select bool_or(source = 'demo') from stock_prices) as has_demo_prices,
               (select bool_or(provider = 'demo') from news_articles) as has_demo_news""",
    )[0]
    models = _rows(engine, "select name, version, config from model_versions order by id")
    return {
        **r,
        "demo_mode": get_settings().demo_mode,
        "disclaimer": DISCLAIMER,
        "aggregation": {"method_version": AGG_VERSION, **AGG_CONFIG},
        "models": models,
        "timezone_note": "Timestamps are UTC; market dates are US/Eastern trading days.",
    }


@app.get("/api/companies")
def companies(request: Request, engine: Engine = Depends(read_engine)) -> list[dict]:
    return _rows(engine, q.SCREENER, mv=AGG_VERSION)


@app.get("/api/companies/{ticker}")
def company(request: Request, ticker: str = TickerPath, engine: Engine = Depends(read_engine)):
    rows = [r for r in _rows(engine, q.SCREENER, mv=AGG_VERSION) if r["ticker"] == ticker]
    if not rows:
        raise HTTPException(404, "Unknown ticker")
    bench = next(
        (r for r in _rows(engine, q.SCREENER, mv=AGG_VERSION) if r["ticker"] == "QQQ"), None
    )
    rel = {}
    for k in ("perf_1m", "perf_3m", "perf_1y"):
        a, b = rows[0].get(k), bench.get(k) if bench else None
        both = a is not None and b is not None
        rel[k.replace("perf", "vs_qqq")] = float(a) - float(b) if both else None
    return {**rows[0], **rel, "benchmark": "QQQ"}


@app.get("/api/companies/{ticker}/prices")
def prices(
    request: Request,
    ticker: str = TickerPath,
    start: date | None = None,
    end: date | None = None,
    engine: Engine = Depends(read_engine),
) -> list[dict]:
    cid = _company_id(engine, ticker)
    end = end or date.today()
    start = start or end - timedelta(days=400)
    if start > end or (end - start).days > 3 * 366:
        raise HTTPException(422, "Invalid date range (max 3 years)")
    return _rows(engine, q.PRICES, cid=cid, start=start, end=end)


@app.get("/api/companies/{ticker}/sentiment")
def sentiment_history(
    request: Request, ticker: str = TickerPath, engine: Engine = Depends(read_engine)
) -> list[dict]:
    cid = _company_id(engine, ticker)
    return _rows(
        engine,
        """select as_of, score, label, n_articles, n_unique_stories
                            from aggregated_sentiment where company_id = :c and method_version = :m
                            order by as_of""",
        c=cid,
        m=AGG_VERSION,
    )


@app.get("/api/companies/{ticker}/events")
def events(
    request: Request, ticker: str = TickerPath, engine: Engine = Depends(read_engine)
) -> dict:
    """Chart markers: per-day news counts by label (unique stories) + SEC filings."""
    cid = _company_id(engine, ticker)
    news = _rows(
        engine,
        """
        select (a.published_at at time zone 'America/New_York')::date as day,
               count(*) filter (where p.label = 'bullish') as bullish,
               count(*) filter (where p.label = 'bearish') as bearish,
               count(*) filter (where p.label = 'neutral') as neutral,
               count(*) filter (where p.label = 'insufficient_evidence') as insufficient
        from sentiment_predictions p join news_articles a on a.id = p.article_id
        where p.company_id = :c and a.duplicate_of is null
        group by 1 order by 1""",
        c=cid,
    )
    filings = _rows(
        engine,
        """select form, filed_date, url from sec_filings
                               where company_id = :c order by filed_date""",
        c=cid,
    )
    return {"news": news, "filings": filings}


@app.get("/api/news")
def news(
    request: Request,
    ticker: str | None = Query(default=None, pattern=r"^[A-Z.]{1,10}$"),
    industry: str | None = Query(default=None, max_length=60),
    label: Label | None = None,
    event_type: str | None = Query(default=None, max_length=40),
    source: str | None = Query(default=None, max_length=80),
    start: datetime | None = None,
    end: datetime | None = None,
    q_: str | None = Query(default=None, alias="q", max_length=100),
    include_duplicates: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100_000),
    engine: Engine = Depends(read_engine),
) -> list[dict]:
    q_text = q_.replace("%", r"\%").replace("_", r"\_") if q_ else None
    return _rows(
        engine,
        q.NEWS,
        ticker=ticker,
        industry=industry,
        label=label,
        event_type=event_type,
        source=source,
        start=start,
        end=end,
        q=q_text,
        include_duplicates=include_duplicates,
        limit=limit,
        offset=offset,
    )


@app.get("/api/overview")
def overview(request: Request, engine: Engine = Depends(read_engine)) -> dict:
    rows = [r for r in _rows(engine, q.SCREENER, mv=AGG_VERSION) if not r["is_benchmark"]]
    counts = {
        k: sum(r["sentiment_label"] == k for r in rows)
        for k in ("bullish", "bearish", "neutral", "insufficient_evidence")
    }
    by_ind: dict[str, list[float]] = {}
    for r in rows:
        if r["sentiment_score"] is not None:
            by_ind.setdefault(r["industry"], []).append(float(r["sentiment_score"]))
    sector = [
        {"industry": k, "avg_score": sum(v) / len(v), "companies": len(v)}
        for k, v in sorted(by_ind.items())
    ]
    moves = sorted(
        [r for r in rows if r["change_1d"] is not None], key=lambda r: float(r["change_1d"])
    )
    trend = _rows(
        engine,
        """
        select (as_of at time zone 'America/New_York')::date as day, avg(score) as avg_score,
               count(*) filter (where label = 'bullish') as bullish,
               count(*) filter (where label = 'bearish') as bearish
        from aggregated_sentiment s join companies c on c.id = s.company_id
        where method_version = :m and not c.is_benchmark group by 1 order by 1""",
        m=AGG_VERSION,
    )
    major = _rows(
        engine,
        q.NEWS.replace(
            "order by a.published_at desc",
            "order by abs(p.p_positive - p.p_negative) desc, a.published_at desc",
        ),
        ticker=None,
        industry=None,
        label=None,
        event_type=None,
        source=None,
        start=None,
        end=None,
        q=None,
        include_duplicates=False,
        limit=3000,
        offset=0,
    )
    strong = [m for m in major if m["relevance"] == 1 and not m["needs_review"]]
    # balance the list: the strongest bullish and the strongest bearish stories
    major = sorted(
        [m for m in strong if m["label"] == "bullish"][:4]
        + [m for m in strong if m["label"] == "bearish"][:4],
        key=lambda m: m["published_at"],
        reverse=True,
    )
    return {
        "counts": counts,
        "heatmap": rows,
        "sector": sector,
        "trend": trend,
        "top_gainers": moves[::-1][:5],
        "top_losers": moves[:5],
        "trending": sorted(rows, key=lambda r: -r["news_7d"])[:5],
        "major_events": major,
    }


@app.get("/api/performance")
def performance(request: Request, engine: Engine = Depends(read_engine)) -> dict:
    rows = _rows(
        engine,
        """select e.dataset, e.metrics, e.created_at, mv.name, mv.version
           from model_evaluations e join model_versions mv on mv.id = e.model_version_id
           order by e.created_at""",
    )
    latest = {r["dataset"]: r for r in rows}
    cls, fr = latest.get("manual-eval-v1"), latest.get("forward-returns-v1")
    return {
        "classification": cls["metrics"] if cls else None,
        "classification_at": cls["created_at"] if cls else None,
        "forward_returns": fr["metrics"] if fr else None,
        "forward_returns_at": fr["created_at"] if fr else None,
        "model": f"{rows[-1]['name']} {rows[-1]['version']}" if rows else None,
    }


@app.get("/api/macro")
def macro(request: Request, engine: Engine = Depends(read_engine)) -> list[dict]:
    return _rows(
        engine,
        "select series_id, obs_date, value from macro_observations order by series_id, obs_date",
    )


@app.post("/api/admin/aggregate", dependencies=[Depends(require_admin)])
@limiter.limit("5/hour")
def admin_aggregate(request: Request, engine: Engine = Depends(write_engine)) -> dict:
    from marketlens.jobs.aggregate import run

    return {"rows": run(engine)}
