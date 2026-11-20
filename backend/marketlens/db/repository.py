"""Write helpers used by the pipeline jobs (writer role)."""

from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import Connection, text

from marketlens.universe import Company


def upsert_companies(conn: Connection, companies: list[Company]) -> dict[str, int]:
    ids = {}
    for c in companies:
        row = conn.execute(
            text("""
                insert into companies (ticker, name, aliases, industry, exchange, cik, is_benchmark)
                values (:ticker, :name, :aliases, :industry, :exchange, :cik, :is_benchmark)
                on conflict (ticker) do update set
                  name = excluded.name, aliases = excluded.aliases, industry = excluded.industry,
                  exchange = excluded.exchange, cik = excluded.cik,
                  is_benchmark = excluded.is_benchmark
                returning id
            """),
            {
                "ticker": c.ticker,
                "name": c.name,
                "aliases": list(c.aliases),
                "industry": c.industry,
                "exchange": c.exchange,
                "cik": c.cik,
                "is_benchmark": c.is_benchmark,
            },
        ).one()
        ids[c.ticker] = row.id
    return ids


def record_membership(
    conn: Connection,
    company_id: int,
    effective_from: date,
    rank: int | None,
    market_cap_usd: float | None,
    method_version: str,
) -> None:
    """Open a membership period. Any earlier open period for the company is closed first."""
    conn.execute(
        text("""update universe_membership set effective_to = :d
                where company_id = :cid and effective_to is null and effective_from < :d"""),
        {"cid": company_id, "d": effective_from},
    )
    conn.execute(
        text("""
            insert into universe_membership
              (company_id, effective_from, rank, market_cap_usd, method_version)
            values (:cid, :d, :rank, :mcap, :mv)
            on conflict (company_id, effective_from) do update set
              rank = excluded.rank, market_cap_usd = excluded.market_cap_usd,
              method_version = excluded.method_version
        """),
        {
            "cid": company_id,
            "d": effective_from,
            "rank": rank,
            "mcap": market_cap_usd,
            "mv": method_version,
        },
    )


def upsert_prices(conn: Connection, company_id: int, prices: pd.DataFrame, source: str) -> int:
    """prices: columns trade_date, open, high, low, close, volume[, adj_close]."""
    rows = [
        {
            "cid": company_id,
            "d": r.trade_date,
            "o": float(r.open),
            "h": float(r.high),
            "l": float(r.low),
            "c": float(r.close),
            "ac": float(getattr(r, "adj_close", r.close)),
            "v": int(r.volume),
            "src": source,
        }
        for r in prices.itertuples(index=False)
    ]
    if rows:
        conn.execute(
            text("""
                insert into stock_prices
                  (company_id, trade_date, open, high, low, close, adj_close, volume, source)
                values (:cid, :d, :o, :h, :l, :c, :ac, :v, :src)
                on conflict (company_id, trade_date) do update set
                  open = excluded.open, high = excluded.high, low = excluded.low,
                  close = excluded.close, adj_close = excluded.adj_close,
                  volume = excluded.volume, source = excluded.source, ingested_at = now()
            """),
            rows,
        )
    return len(rows)


# --- ingestion logs -------------------------------------------------------------------------


def log_start(conn: Connection, job: str, provider: str | None) -> int:
    return conn.execute(
        text(
            "insert into ingestion_logs (job, provider, status) values (:j, :p, 'running') "
            "returning id"
        ),
        {"j": job, "p": provider},
    ).scalar_one()


def log_finish(
    conn: Connection,
    log_id: int,
    status: str,
    rows: int,
    api_calls: int,
    error: str | None = None,
) -> None:
    from marketlens.logging_utils import redact

    conn.execute(
        text("""update ingestion_logs set finished_at = now(), status = :s, rows_upserted = :r,
                api_calls = :a, error_summary = :e where id = :id"""),
        {
            "s": status,
            "r": rows,
            "a": api_calls,
            "e": redact(error)[:500] if error else None,
            "id": log_id,
        },
    )


# --- filings & macro ------------------------------------------------------------------------


def upsert_filings(conn: Connection, company_id: int, filings: list) -> int:
    rows = [
        {
            "cid": company_id,
            "acc": f.accession_number,
            "form": f.form,
            "fd": f.filed_date,
            "rd": f.report_date,
            "doc": f.primary_document,
            "url": f.url,
        }
        for f in filings
    ]
    if rows:
        conn.execute(
            text("""
                insert into sec_filings (company_id, accession_number, form, filed_date,
                                         report_date, primary_document, url)
                values (:cid, :acc, :form, :fd, :rd, :doc, :url)
                on conflict (accession_number) do nothing
            """),
            rows,
        )
    return len(rows)


def upsert_macro(conn: Connection, series_id: str, df: pd.DataFrame, source: str) -> int:
    rows = [
        {
            "s": series_id,
            "d": r.obs_date,
            "v": None if pd.isna(r.value) else float(r.value),
            "src": source,
        }
        for r in df.itertuples(index=False)
    ]
    if rows:
        conn.execute(
            text("""insert into macro_observations (series_id, obs_date, value, source)
                    values (:s, :d, :v, :src)
                    on conflict (series_id, obs_date) do update set value = excluded.value"""),
            rows,
        )
    return len(rows)
