"""FRED macro series via the public, keyless CSV export (fredgraph.csv)."""

from __future__ import annotations

import io
from datetime import date

import httpx
import pandas as pd

from marketlens.providers.http import ApiClient

DEFAULT_SERIES = {
    "DGS10": "10-Year Treasury yield (%)",
    "FEDFUNDS": "Effective federal funds rate (%)",
    "CPIAUCSL": "CPI, all urban consumers (index)",
}


class FredCsvProvider:
    name = "fred"

    def __init__(self, transport: httpx.BaseTransport | None = None):
        self.client = ApiClient(self.name, "https://fred.stlouisfed.org", 30, transport=transport)

    def series(self, series_id: str, start: date) -> pd.DataFrame:
        resp = self.client.get("/graph/fredgraph.csv", {"id": series_id, "cosd": start.isoformat()})
        df = pd.read_csv(io.StringIO(resp.text))
        df.columns = ["obs_date", "value"]
        df["obs_date"] = pd.to_datetime(df["obs_date"]).dt.date
        df["value"] = pd.to_numeric(df["value"], errors="coerce")  # '.' = missing
        return df[df["obs_date"] >= start].reset_index(drop=True)
