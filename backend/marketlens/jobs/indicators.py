"""Compute indicators for every company from stored prices.

python -m marketlens.jobs.indicators
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from marketlens.db import get_engine
from marketlens.db.repository import log_finish, log_start, upsert_indicators
from marketlens.indicators import compute_indicators


def run(engine=None) -> int:
    engine = engine or get_engine()
    with engine.begin() as conn:
        log_id = log_start(conn, "indicators", None)
        total = 0
        company_ids = [r[0] for r in conn.execute(text("select id from companies"))]
        for cid in company_ids:
            prices = pd.read_sql(
                text(
                    "select trade_date, high, low, close from stock_prices "
                    "where company_id = :c order by trade_date"
                ),
                conn,
                params={"c": cid},
            )
            if not prices.empty:
                total += upsert_indicators(conn, cid, compute_indicators(prices))
        log_finish(conn, log_id, "success", total, 0)
    return total


if __name__ == "__main__":
    print(f"indicators: {run()} rows")
