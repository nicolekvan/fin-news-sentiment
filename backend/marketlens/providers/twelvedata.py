"""Twelve Data: daily OHLCV. Free tier: 8 credits/min, 800/day, 1 credit per symbol."""

from __future__ import annotations

from datetime import date

import httpx
import pandas as pd

from marketlens.config import get_settings
from marketlens.providers.base import ProviderError, ProviderNotConfigured
from marketlens.providers.http import ApiClient


class TwelveDataProvider:
    name = "twelvedata"

    def __init__(self, transport: httpx.BaseTransport | None = None, calls_per_minute: float = 7):
        key = get_settings().twelve_data_api_key
        if key is None:
            raise ProviderNotConfigured("TWELVE_DATA_API_KEY not set")
        self.client = ApiClient(
            self.name,
            "https://api.twelvedata.com",
            calls_per_minute,
            headers={"Authorization": f"apikey {key.get_secret_value()}"},
            transport=transport,
        )

    def daily_bars(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        d = self.client.get(
            "/time_series",
            {
                "symbol": ticker,
                "interval": "1day",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "outputsize": 5000,
                "order": "ASC",
            },
        ).json()
        if d.get("status") != "ok":
            # Twelve Data returns HTTP 200 with an error body; never echo the request.
            raise ProviderError(
                f"twelvedata {ticker}: {d.get('code')} {str(d.get('message'))[:80]}"
            )
        df = pd.DataFrame(d.get("values", []))
        if df.empty:
            return df
        df = df.rename(columns={"datetime": "trade_date"})
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
        for col in ("open", "high", "low", "close"):
            df[col] = df[col].astype(float)
        df["volume"] = df["volume"].astype(float).astype("int64")
        return df[["trade_date", "open", "high", "low", "close", "volume"]].sort_values(
            "trade_date", ignore_index=True
        )
