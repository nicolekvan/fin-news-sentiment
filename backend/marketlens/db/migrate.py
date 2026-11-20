"""Minimal migration runner for `supabase/migrations/NNNN_name.{up,down}.sql`.

python -m marketlens.db.migrate up
python -m marketlens.db.migrate down   # rolls back the latest migration
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import Engine, text

from marketlens.db import get_engine

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "supabase" / "migrations"


def _run_raw(conn, sql: str) -> None:
    # Send the file verbatim: no parameter parsing, so `%I` in format() calls is safe.
    conn.connection.driver_connection.execute(sql)


def _migrations() -> list[str]:
    return sorted(p.name.removesuffix(".up.sql") for p in MIGRATIONS_DIR.glob("*.up.sql"))


def _ensure_table(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "create table if not exists schema_migrations "
                "(name text primary key, applied_at timestamptz not null default now())"
            )
        )


def applied(engine: Engine) -> list[str]:
    _ensure_table(engine)
    with engine.connect() as conn:
        return [
            r[0] for r in conn.execute(text("select name from schema_migrations order by name"))
        ]


def up(engine: Engine) -> list[str]:
    done = set(applied(engine))
    ran = []
    for name in _migrations():
        if name in done:
            continue
        sql = (MIGRATIONS_DIR / f"{name}.up.sql").read_text()
        with engine.begin() as conn:  # each migration is atomic
            _run_raw(conn, sql)
            conn.execute(text("insert into schema_migrations (name) values (:n)"), {"n": name})
        ran.append(name)
    return ran


def down(engine: Engine) -> str | None:
    done = applied(engine)
    if not done:
        return None
    name = done[-1]
    sql = (MIGRATIONS_DIR / f"{name}.down.sql").read_text()
    with engine.begin() as conn:
        _run_raw(conn, sql)
        conn.execute(text("delete from schema_migrations where name = :n"), {"n": name})
    return name


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("direction", choices=["up", "down"])
    args = ap.parse_args()
    engine = get_engine(writer=True)
    if args.direction == "up":
        print("applied:", up(engine) or "nothing to do")
    else:
        print("rolled back:", down(engine) or "nothing to do")


if __name__ == "__main__":
    main()
