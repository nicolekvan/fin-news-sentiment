"""Finnhub: company news + company profile (market cap). Free tier: 60 calls/min."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import httpx

from marketlens.config import get_settings
from marketlens.providers.base import CompanyProfile, ProviderNotConfigured, RawNewsItem
from marketlens.providers.http import ApiClient


class FinnhubProvider:
    name = "finnhub"

    def __init__(self, transport: httpx.BaseTransport | None = None, calls_per_minute: float = 55):
        key = get_settings().finnhub_api_key
        if key is None:
            raise ProviderNotConfigured("FINNHUB_API_KEY not set")
        self.client = ApiClient(
            self.name,
            "https://finnhub.io/api/v1",
            calls_per_minute,
            headers={"X-Finnhub-Token": key.get_secret_value()},
            transport=transport,
        )

    def company_news(self, ticker: str, start: date, end: date) -> list[RawNewsItem]:
        """One request per day: Finnhub caps each response at ~250 items."""
        items: dict[str, RawNewsItem] = {}
        day = start
        while day <= end:
            resp = self.client.get(
                "/company-news", {"symbol": ticker, "from": day.isoformat(), "to": day.isoformat()}
            )
            for raw in resp.json() or []:
                item = _parse_news(raw)
                if item is not None:
                    items[item.provider_article_id] = item
            day += timedelta(days=1)
        return sorted(items.values(), key=lambda i: i.published_at)

    def profile(self, ticker: str) -> CompanyProfile:
        d = self.client.get("/stock/profile2", {"symbol": ticker}).json() or {}
        mcap = d.get("marketCapitalization")  # reported in USD millions
        return CompanyProfile(
            ticker=ticker,
            name=d.get("name") or ticker,
            market_cap_usd=float(mcap) * 1e6 if mcap else None,
            industry=d.get("finnhubIndustry"),
        )


def _parse_news(raw: dict) -> RawNewsItem | None:
    try:
        headline = (raw.get("headline") or "").strip()
        url = (raw.get("url") or "").strip()
        if not headline or not url.startswith("http"):
            return None
        related = tuple(t.strip().upper() for t in (raw.get("related") or "").split(",") if t)
        return RawNewsItem(
            provider="finnhub",
            provider_article_id=str(raw["id"]),
            url=url,
            headline=headline,
            summary=(raw.get("summary") or "").strip(),
            source_name=(raw.get("source") or "Unknown").strip(),
            published_at=datetime.fromtimestamp(int(raw["datetime"]), tz=UTC),
            related_tickers=related,
        )
    except (KeyError, TypeError, ValueError):
        return None
