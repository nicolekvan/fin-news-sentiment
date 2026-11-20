from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from marketlens.db import migrate
from marketlens.db.repository import record_membership, upsert_companies, upsert_prices
from marketlens.demo import demo_prices
from marketlens.universe import load_universe


def test_all_migrations_applied(engine):
    assert migrate.applied(engine) == ["0001_init", "0002_roles_rls"]


def test_seed_companies_and_prices(conn):
    ids = upsert_companies(conn, load_universe(dev_only=True))
    assert len(ids) == 12
    n = upsert_prices(conn, ids["NVDA"], demo_prices("NVDA"), "demo")
    assert conn.execute(text("select count(*) from stock_prices")).scalar() == n
    # idempotent
    upsert_prices(conn, ids["NVDA"], demo_prices("NVDA"), "demo")
    assert conn.execute(text("select count(*) from stock_prices")).scalar() == n


def test_membership_history_preserved(conn):
    ids = upsert_companies(conn, load_universe(dev_only=True))
    record_membership(conn, ids["AMD"], date(2026, 8, 1), 8, 3.0e11, "universe-v1")
    record_membership(conn, ids["AMD"], date(2026, 11, 20), 7, 3.5e11, "universe-v1")
    rows = conn.execute(
        text(
            "select effective_from, effective_to from universe_membership "
            "where company_id = :c order by effective_from"
        ),
        {"c": ids["AMD"]},
    ).all()
    assert rows == [(date(2026, 8, 1), date(2026, 11, 20)), (date(2026, 11, 20), None)]


@pytest.mark.parametrize(
    "sql",
    [
        # second share class of an issuer already present (same CIK)
        "insert into companies (ticker,name,industry,cik) "
        "values ('GOOG','Alphabet C','x','0001652044')",
        # non-benchmark without CIK
        "insert into companies (ticker,name,industry) values ('XYZ','No CIK','x')",
    ],
)
def test_company_constraints(conn, sql):
    upsert_companies(conn, load_universe(dev_only=True))
    with pytest.raises(IntegrityError):
        conn.execute(text(sql))


def test_invalid_label_rejected(conn):
    with pytest.raises(IntegrityError):
        conn.execute(
            text(
                "insert into aggregated_sentiment (company_id, as_of, method_version, score, label,"
                " n_articles, n_unique_stories) values (1, now(), 'v', 0.1, 'very_bullish', 1, 1)"
            )
        )


def test_reader_role_is_read_only(conn):
    upsert_companies(conn, load_universe(dev_only=True))
    conn.execute(text("set local role marketlens_reader"))
    assert conn.execute(text("select count(*) from companies")).scalar() == 12
    with pytest.raises(DBAPIError, match="permission denied"):
        conn.execute(text("insert into llm_usage (usage_date) values (current_date)"))


def test_reader_cannot_see_operational_tables(conn):
    conn.execute(text("set local role marketlens_reader"))
    with pytest.raises(DBAPIError, match="permission denied"):
        conn.execute(text("select * from ingestion_logs"))


def test_down_then_up_roundtrip(engine):
    assert migrate.down(engine) == "0002_roles_rls"
    assert migrate.down(engine) == "0001_init"
    assert migrate.applied(engine) == []
    assert migrate.up(engine) == ["0001_init", "0002_roles_rls"]
