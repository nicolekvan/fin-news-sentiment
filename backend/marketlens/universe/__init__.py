"""Company universe: load and validate `config/universe.csv`."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "config" / "universe.csv"
METHOD_VERSION = "universe-v1"


@dataclass(frozen=True)
class Company:
    ticker: str
    name: str
    industry: str
    exchange: str
    cik: str | None
    is_benchmark: bool
    dev_set: bool
    aliases: tuple[str, ...] = field(default_factory=tuple)


def _bool(value: str) -> bool:
    if value.strip().lower() not in ("true", "false"):
        raise ValueError(f"expected true/false, got {value!r}")
    return value.strip().lower() == "true"


def load_universe(path: Path = DEFAULT_PATH, dev_only: bool = False) -> list[Company]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    companies = [
        Company(
            ticker=r["ticker"].strip().upper(),
            name=r["name"].strip(),
            aliases=tuple(a.strip() for a in r["aliases"].split("|") if a.strip()),
            industry=r["industry"].strip(),
            exchange=r["exchange"].strip(),
            cik=r["cik"].strip() or None,
            is_benchmark=_bool(r["is_benchmark"]),
            dev_set=_bool(r["dev_set"]),
        )
        for r in rows
    ]
    validate(companies)
    return [c for c in companies if c.dev_set] if dev_only else companies


def validate(companies: list[Company]) -> None:
    tickers = [c.ticker for c in companies]
    if len(set(tickers)) != len(tickers):
        raise ValueError("duplicate ticker in universe")
    ciks = [c.cik for c in companies if c.cik]
    if len(set(ciks)) != len(ciks):
        raise ValueError(
            "duplicate CIK: an issuer is listed more than once (share-class double count)"
        )
    for c in companies:
        if not c.is_benchmark and not (c.cik and c.cik.isdigit() and len(c.cik) == 10):
            raise ValueError(f"{c.ticker}: non-benchmark companies need a 10-digit CIK")
