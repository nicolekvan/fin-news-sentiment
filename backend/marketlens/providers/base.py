"""Provider interfaces. Each data domain is a Protocol so adapters are swappable."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

import pandas as pd


class ProviderError(RuntimeError):
    """A provider call failed after retries. Messages never contain credentials."""


class ProviderNotConfigured(ProviderError):
    pass


@dataclass(frozen=True)
class RawNewsItem:
    provider: str
    provider_article_id: str
    url: str
    headline: str
    summary: str
    source_name: str
    published_at: datetime  # timezone-aware UTC
    related_tickers: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompanyProfile:
    ticker: str
    name: str
    market_cap_usd: float | None
    industry: str | None


@dataclass(frozen=True)
class Filing:
    accession_number: str
    form: str
    filed_date: date
    report_date: date | None
    primary_document: str | None
    url: str


class NewsProvider(Protocol):
    name: str

    def company_news(self, ticker: str, start: date, end: date) -> list[RawNewsItem]: ...


class PriceProvider(Protocol):
    name: str

    def daily_bars(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        """Columns: trade_date, open, high, low, close, volume (ascending by date)."""
        ...


class ProfileProvider(Protocol):
    name: str

    def profile(self, ticker: str) -> CompanyProfile: ...


class FilingsProvider(Protocol):
    name: str

    def recent_filings(self, cik: str, forms: tuple[str, ...], since: date) -> list[Filing]: ...


class MacroProvider(Protocol):
    name: str

    def series(self, series_id: str, start: date) -> pd.DataFrame:
        """Columns: obs_date, value."""
        ...
