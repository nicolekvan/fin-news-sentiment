"""One-time data pull for the snapshot.

    python -m marketlens.jobs.pull --snapshot 2026-11-20 \
        [--steps profiles,prices,news,filings,macro]

Raw news is cached as JSONL under data/cache/ (gitignored) so the news pipeline can be re-run
offline without spending API quota again. Every step is recorded in ingestion_logs.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

from marketlens.config import get_settings
from marketlens.db import get_engine
from marketlens.db import repository as repo
from marketlens.logging_utils import configure_logging
from marketlens.providers.base import ProviderError, ProviderNotConfigured
from marketlens.universe import METHOD_VERSION, load_universe

log = logging.getLogger("marketlens.pull")
CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache"
PRICE_HISTORY_DAYS = 460  # ~1 year shown + warm-up for the 200-day moving average
NEWS_DAYS = 90
FILING_FORMS = ("8-K", "10-Q", "10-K")


def news_cache_path(ticker: str, snapshot: date) -> Path:
    return CACHE_DIR / f"news_{ticker}_{snapshot.isoformat()}.jsonl"


def run(snapshot: date, steps: set[str], engine=None) -> None:
    engine = engine or get_engine()
    companies = load_universe()
    stocks = [c for c in companies if not c.is_benchmark]
    with engine.begin() as conn:
        ids = repo.upsert_companies(conn, companies)

    def step(job, provider_factory, body):
        with engine.begin() as conn:
            log_id = repo.log_start(conn, job, None)
        rows, calls, status, err = 0, 0, "success", None
        try:
            provider = provider_factory()
            rows, calls, failures = body(provider)
            if failures:
                status, err = "partial", "; ".join(failures)
        except ProviderNotConfigured as exc:
            status, err = "failed", f"skipped: {exc}"
        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed silently
            status, err = "failed", str(exc)
        with engine.begin() as conn:
            repo.log_finish(conn, log_id, status, rows, calls, err)
        log.info(
            "%s: %s, %d rows, %d API calls%s", job, status, rows, calls, f" ({err})" if err else ""
        )

    if "profiles" in steps:
        from marketlens.providers.finnhub import FinnhubProvider

        def profiles(p):
            caps = {c.ticker: p.profile(c.ticker, c.adr_ratio).market_cap_usd for c in stocks}
            ranked = sorted((t for t in caps if caps[t]), key=lambda t: -caps[t])
            with engine.begin() as conn:
                for rank, t in enumerate(ranked, 1):
                    repo.record_membership(conn, ids[t], snapshot, rank, caps[t], METHOD_VERSION)
            missing = [t for t in caps if not caps[t]]
            return len(ranked), p.client.calls, [f"no market cap: {missing}"] if missing else []

        step("profiles", FinnhubProvider, profiles)

    if "prices" in steps:
        from marketlens.providers.twelvedata import TwelveDataProvider

        def prices(p):
            rows, failures = 0, []
            start = snapshot - timedelta(days=PRICE_HISTORY_DAYS)
            for c in companies:
                try:
                    df = p.daily_bars(c.ticker, start, snapshot)
                    with engine.begin() as conn:
                        rows += repo.upsert_prices(conn, ids[c.ticker], df, p.name)
                except ProviderError as exc:
                    failures.append(str(exc))
            return rows, p.client.calls, failures

        step("prices", TwelveDataProvider, prices)

    if "news" in steps:
        from marketlens.providers.finnhub import FinnhubProvider

        def news(p):
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            rows, failures = 0, []
            for c in stocks:
                path = news_cache_path(c.ticker, snapshot)
                if path.exists():
                    log.info("news %s: using cache %s", c.ticker, path.name)
                    continue
                try:
                    items = p.company_news(c.ticker, snapshot - timedelta(days=NEWS_DAYS), snapshot)
                except ProviderError as exc:
                    failures.append(str(exc))
                    continue
                tmp = path.with_suffix(".tmp")
                with open(tmp, "w", encoding="utf-8") as f:
                    for it in items:
                        d = asdict(it)
                        d["published_at"] = it.published_at.isoformat()
                        f.write(json.dumps(d) + "\n")
                tmp.rename(path)  # only complete files count as cached
                rows += len(items)
                log.info("news %s: %d items", c.ticker, len(items))
            return rows, p.client.calls, failures

        step("news_raw", FinnhubProvider, news)

    if "filings" in steps:
        from marketlens.providers.edgar import EdgarProvider

        def filings(p):
            rows = 0
            for c in stocks:
                fs = p.recent_filings(c.cik, FILING_FORMS, snapshot - timedelta(days=365))
                with engine.begin() as conn:
                    rows += repo.upsert_filings(conn, ids[c.ticker], fs)
            return rows, p.client.calls, []

        step("filings", EdgarProvider, filings)

    if "macro" in steps:
        from marketlens.providers.fred import DEFAULT_SERIES, FredCsvProvider

        def macro(p):
            rows = 0
            for sid in DEFAULT_SERIES:
                df = p.series(sid, snapshot - timedelta(days=PRICE_HISTORY_DAYS))
                with engine.begin() as conn:
                    rows += repo.upsert_macro(conn, sid, df, p.name)
            return rows, p.client.calls, []

        step("macro", FredCsvProvider, macro)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=date.fromisoformat, required=True)
    ap.add_argument("--steps", default="profiles,prices,news,filings,macro")
    args = ap.parse_args()
    configure_logging()
    if get_settings().demo_mode:
        raise SystemExit("DEMO_MODE is on: refusing to call live providers (set DEMO_MODE=false)")
    run(args.snapshot, set(args.steps.split(",")))


if __name__ == "__main__":
    main()
