"""Deterministic synthetic data for DEMO MODE.

Everything produced here is fake and labelled as such: source 'demo', publisher
'Demo Wire (synthetic)', URLs under the reserved example.com domain.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEMO_SOURCE = "demo"
DEMO_PUBLISHER = "Demo Wire (synthetic)"

_TEMPLATES = {
    "bullish": [
        "{name} beats quarterly revenue estimates and raises full-year guidance",
        "{name} wins multi-year contract with a major cloud customer",
    ],
    "bearish": [
        "{name} cuts outlook as demand weakens in key segment",
        "{name} faces regulatory probe over competitive practices",
    ],
    "neutral": [
        "{name} schedules annual shareholder meeting",
        "{name} appoints new head of investor relations",
    ],
}


def demo_prices(ticker: str, start: str = "2025-11-20", end: str = "2026-11-20") -> pd.DataFrame:
    """Geometric Brownian motion OHLCV on business days, seeded by ticker."""
    rng = np.random.default_rng(_seed(ticker))
    dates = pd.bdate_range(start, end)
    rets = rng.normal(0.0004, 0.02, len(dates))
    close = 100 * np.exp(np.cumsum(rets))
    open_ = close * (1 + rng.normal(0, 0.005, len(dates)))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.008, len(dates))))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.008, len(dates))))
    volume = rng.integers(5_000_000, 50_000_000, len(dates))
    return pd.DataFrame(
        {
            "trade_date": dates.date,
            "open": open_.round(4),
            "high": high.round(4),
            "low": low.round(4),
            "close": close.round(4),
            "adj_close": close.round(4),
            "volume": volume,
        }
    )


def demo_news(ticker: str, name: str, n: int = 12, end: str = "2026-11-20") -> pd.DataFrame:
    rng = np.random.default_rng(_seed(ticker) + 1)
    labels = rng.choice(list(_TEMPLATES), size=n)
    hours = np.sort(rng.integers(0, 90 * 24, n))
    ts = pd.Timestamp(end, tz="UTC") - pd.to_timedelta(hours, unit="h")
    rows = []
    for i, (label, t) in enumerate(zip(labels, ts, strict=True)):
        headline = _TEMPLATES[label][i % 2].format(name=name)
        rows.append(
            {
                "provider": DEMO_SOURCE,
                "provider_article_id": f"demo-{ticker}-{i}",
                "url": f"https://example.com/demo/{ticker.lower()}/{i}",
                "headline": f"[DEMO] {headline}",
                "summary": f"Synthetic demo article. {headline}.",
                "source_name": DEMO_PUBLISHER,
                "published_at": t,
                "demo_label": label,
            }
        )
    return pd.DataFrame(rows)


def _seed(ticker: str) -> int:
    # Stable across processes (Python's hash() is randomized per process).
    return sum((i + 1) * ord(ch) for i, ch in enumerate(ticker)) * 7919
