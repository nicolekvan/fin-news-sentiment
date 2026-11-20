"""Compute daily company-level sentiment for every trading day in the news window.

python -m marketlens.jobs.aggregate
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from marketlens.aggregate import METHOD_VERSION, daily_aggregates
from marketlens.db import get_engine
from marketlens.db.repository import log_finish, log_start

PREDS_SQL = """
select p.company_id, coalesce(a.duplicate_of, a.id) as story_id, a.published_at,
       p.p_positive, p.p_negative, ac.relevance, p.confidence, p.label, p.needs_review
from sentiment_predictions p
join news_articles a on a.id = p.article_id
join article_companies ac on ac.article_id = p.article_id and ac.company_id = p.company_id
"""


def run(engine=None) -> int:
    engine = engine or get_engine()
    with engine.begin() as conn:
        log_id = log_start(conn, "aggregate", None)
        preds = pd.read_sql(text(PREDS_SQL), conn)
        if preds.empty:
            log_finish(conn, log_id, "success", 0, 0)
            return 0
        preds["published_at"] = pd.to_datetime(preds.published_at, utc=True)
        for col in ("p_positive", "p_negative", "relevance", "confidence"):
            preds[col] = preds[col].astype(float)
        start = preds.published_at.min().date()
        days = [
            d.date()
            for d in pd.read_sql(
                text(
                    "select distinct trade_date from stock_prices where trade_date >= :s order by 1"
                ),
                conn,
                params={"s": start},
            ).trade_date.map(pd.Timestamp)
        ]
        conn.execute(
            text("delete from aggregated_sentiment where method_version = :m"),
            {"m": METHOD_VERSION},
        )
        rows = []
        for cid, group in preds.groupby("company_id"):
            for agg in daily_aggregates(group, days):
                rows.append({"c": int(cid), "m": METHOD_VERSION, **agg})
        conn.execute(
            text("""
            insert into aggregated_sentiment (company_id, as_of, method_version, score, label,
              n_articles, n_unique_stories)
            values (:c, :as_of, :m, :score, :label, :n_articles, :n_unique_stories)"""),
            rows,
        )
        log_finish(conn, log_id, "success", len(rows), 0)
    return len(rows)


if __name__ == "__main__":
    print(f"aggregated rows: {run()}")
