"""Seed companies from config/universe.csv; optionally load synthetic demo prices.

python -m marketlens.jobs.seed            # companies only
python -m marketlens.jobs.seed --demo     # + synthetic demo prices (labelled 'demo')
"""

from __future__ import annotations

import argparse

from marketlens.db import get_engine
from marketlens.db.repository import upsert_companies, upsert_prices
from marketlens.demo import DEMO_SOURCE, demo_prices
from marketlens.universe import load_universe


def seed(engine, demo: bool = False, dev_only: bool | None = None) -> dict[str, int]:
    companies = load_universe(dev_only=dev_only)
    with engine.begin() as conn:
        ids = upsert_companies(conn, companies)
        if demo:
            for c in companies:
                upsert_prices(conn, ids[c.ticker], demo_prices(c.ticker), DEMO_SOURCE)
    return ids


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--all", action="store_true", help="full universe, not just the dev set")
    args = ap.parse_args()
    ids = seed(get_engine(), demo=args.demo, dev_only=False if args.all else None)
    print(f"seeded {len(ids)} companies" + (" with demo prices" if args.demo else ""))


if __name__ == "__main__":
    main()
