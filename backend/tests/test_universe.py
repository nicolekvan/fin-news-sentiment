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


def test_full_universe_is_top_50_with_benchmarks():
    full = load_universe(dev_only=False)
    stocks = [c for c in full if not c.is_benchmark]
    assert len(stocks) == 50
    assert len({c.cik for c in stocks}) == 50
    by = {c.ticker: c for c in full}
    assert by["TSM"].adr_ratio == 5 and by["BABA"].adr_ratio == 8 and by["AAPL"].adr_ratio == 1
    assert by["NOW"].bare_ticker is False and by["NVDA"].bare_ticker is True


def test_scope_setting_selects_dev_or_full(monkeypatch):
    from marketlens.config import get_settings

    monkeypatch.setenv("UNIVERSE_SCOPE", "dev")
    get_settings.cache_clear()
    assert len([c for c in load_universe() if not c.is_benchmark]) == 10
    monkeypatch.setenv("UNIVERSE_SCOPE", "full")
    get_settings.cache_clear()
    assert len([c for c in load_universe() if not c.is_benchmark]) == 50
    get_settings.cache_clear()
