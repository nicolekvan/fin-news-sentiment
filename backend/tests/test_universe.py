from dataclasses import replace

import pytest

from marketlens.universe import load_universe, validate


def test_dev_set_has_ten_companies_plus_benchmarks():
    dev = load_universe(dev_only=True)
    assert len([c for c in dev if not c.is_benchmark]) == 10
    assert {c.ticker for c in dev if c.is_benchmark} == {"QQQ", "SPY"}


def test_one_security_per_issuer():
    tickers = {c.ticker for c in load_universe()}
    assert "GOOGL" in tickers and "GOOG" not in tickers


def test_duplicate_cik_rejected():
    companies = load_universe()
    googl = next(c for c in companies if c.ticker == "GOOGL")
    with pytest.raises(ValueError, match="duplicate CIK"):
        validate(companies + [replace(googl, ticker="GOOG")])


def test_non_benchmark_requires_cik():
    c = replace(load_universe()[0], cik=None)
    with pytest.raises(ValueError, match="CIK"):
        validate([c])
