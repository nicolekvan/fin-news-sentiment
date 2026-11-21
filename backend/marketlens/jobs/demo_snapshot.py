"""Build a fully synthetic DEMO snapshot (safe to publish and to commit).

    python -m marketlens.jobs.demo_snapshot --db postgresql+psycopg://.../marketlens_demo \
        --out ../frontend/snapshots/demo

Synthetic prices and headlines (clearly labelled [DEMO]) go through the real pipeline:
indicators, news linking, FinBERT scoring, aggregation and export.
"""

from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, text

from marketlens.db import migrate
from marketlens.demo import demo_news
from marketlens.jobs import aggregate, evaluate, indicators, news
from marketlens.jobs.seed import seed
from marketlens.universe import load_universe

SNAPSHOT = date(2026, 11, 20)


def build(db_url: str, out: Path, model=None) -> dict:
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("drop schema public cascade; create schema public"))
    migrate.up(engine)
    seed(engine, demo=True)
    indicators.run(engine)
    raw = []
    for c in load_universe(dev_only=True):
        if c.is_benchmark:
            continue
        for r in demo_news(c.ticker, c.aliases[0], n=40).itertuples():
            raw.append(
                {
                    "provider": "demo",
                    "provider_article_id": r.provider_article_id,
                    "url": r.url,
                    "headline": r.headline,
                    "summary": r.summary,
                    "source_name": r.source_name,
                    "published_at": r.published_at.isoformat(),
                    "related_tickers": [c.ticker],
                }
            )
    stats = news.run(SNAPSHOT, engine=engine, model=model, raw=raw)
    aggregate.run(engine)
    evaluate.run(None, engine=engine)  # forward returns only; demo has no human labels

    os.environ["DATABASE_URL_READONLY"] = db_url
    os.environ["DEMO_MODE"] = "true"
    from marketlens.api.deps import read_engine
    from marketlens.config import get_settings
    from marketlens.jobs import export

    get_settings.cache_clear()
    read_engine.cache_clear()
    return {**stats, **export.run(out)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="a disposable database: it is wiped")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    print(build(args.db, args.out))


if __name__ == "__main__":
    main()
