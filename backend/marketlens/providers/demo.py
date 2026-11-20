"""Demo provider: synthetic, clearly labelled data for DEMO MODE."""

from __future__ import annotations

from datetime import date

import pandas as pd

from marketlens.demo import demo_news, demo_prices
from marketlens.providers.base import CompanyProfile, RawNewsItem


class DemoProvider:
    name = "demo"

    def __init__(self, names: dict[str, str] | None = None):
        self.names = names or {}

    def company_news(self, ticker: str, start: date, end: date) -> list[RawNewsItem]:
        df = demo_news(ticker, self.names.get(ticker, ticker), end=end.isoformat())
        df = df[df.published_at.dt.date >= start]
        return [
            RawNewsItem(
                provider="demo",
                provider_article_id=r.provider_article_id,
                url=r.url,
                headline=r.headline,
                summary=r.summary,
                source_name=r.source_name,
                published_at=r.published_at.to_pydatetime(),
                related_tickers=(ticker,),
            )
            for r in df.itertuples()
        ]

    def daily_bars(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        df = demo_prices(ticker, start.isoformat(), end.isoformat())
        return df[["trade_date", "open", "high", "low", "close", "volume"]]

    def profile(self, ticker: str) -> CompanyProfile:
        return CompanyProfile(ticker, self.names.get(ticker, ticker), None, None)
