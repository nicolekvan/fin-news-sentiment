"""What did stocks do after bullish and bearish classifications? (historical association)

No look-ahead: an article's entry point is the first daily close (16:00 US/Eastern) that comes
after its publication time, so after-hours and weekend news enter at the next session's close.
Forward return over h trading days = close[t+h] / close[t] - 1; benchmark-relative = that minus
QQQ's return over the same dates.

Unit of analysis is the company-day: all non-duplicate, non-review directional predictions for
a company with the same entry date are netted (bullish count - bearish count) into one signal.
Article-level rows are not independent (dozens of stories on the same day share one return),
so they are reported only as a secondary view. Confidence intervals are bootstrap intervals
over company-days. This is a description of the past, not evidence of predictive power.
"""

from __future__ import annotations

from datetime import time

import numpy as np
import pandas as pd

HORIZONS = (1, 5, 20)
CLOSE_ET = time(16, 0)
ET = "America/New_York"


def entry_dates(published_at: pd.Series, trading_days: pd.DatetimeIndex) -> pd.Series:
    """Map UTC publication times to the first trading day whose 16:00 ET close is after them."""
    local = pd.to_datetime(published_at, utc=True).dt.tz_convert(ET)
    day = local.dt.normalize().dt.tz_localize(None)
    after_close = local.dt.time >= CLOSE_ET
    candidate = day + pd.to_timedelta(after_close.astype(int), unit="D")
    idx = trading_days.searchsorted(candidate.values)  # first trading day >= candidate
    out = pd.Series(pd.NaT, index=published_at.index, dtype="datetime64[ns]")
    ok = idx < len(trading_days)
    out[ok] = trading_days[idx[ok]]
    return out


def forward_returns(closes: pd.DataFrame, bench: str = "QQQ") -> dict[int, pd.DataFrame]:
    """closes: index = trading days, columns = tickers. Returns per-horizon frames of
    benchmark-relative and raw forward returns (NaN where the window is incomplete)."""
    out = {}
    for h in HORIZONS:
        raw = closes.shift(-h) / closes - 1
        out[h] = {"raw": raw, "rel": raw.sub(raw[bench], axis=0)}
    return out


def company_day_signals(preds: pd.DataFrame, trading_days: pd.DatetimeIndex) -> pd.DataFrame:
    """preds: ticker, published_at, label, needs_review, duplicate_of."""
    p = preds[
        (preds.duplicate_of.isna())
        & (~preds.needs_review)
        & (preds.label.isin(["bullish", "bearish"]))
    ].copy()
    p["entry"] = entry_dates(p.published_at, trading_days)
    p = p.dropna(subset=["entry"])
    p["v"] = np.where(p.label == "bullish", 1, -1)
    g = p.groupby(["ticker", "entry"]).agg(net=("v", "sum"), n=("v", "size")).reset_index()
    g["signal"] = np.select([g.net > 0, g.net < 0], ["bullish", "bearish"], "mixed")
    return g


def _boot_ci(x: np.ndarray, reps: int = 2000, seed: int = 7) -> tuple[float, float]:
    if len(x) < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = rng.choice(x, size=(reps, len(x)), replace=True).mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def _boot_diff_ci(a: np.ndarray, b: np.ndarray, reps: int = 2000, seed: int = 11):
    if len(a) < 2 or len(b) < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    d = rng.choice(a, (reps, len(a))).mean(axis=1) - rng.choice(b, (reps, len(b))).mean(axis=1)
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def summarize(signals: pd.DataFrame, fwd: dict) -> dict:
    rows, spreads = [], []
    for h in HORIZONS:
        rel, raw = fwd[h]["rel"], fwd[h]["raw"]
        s = signals.copy()
        s["rel"] = [
            rel.at[d, t] if d in rel.index and t in rel.columns else np.nan
            for t, d in zip(s.ticker, s.entry, strict=True)
        ]
        s["raw"] = [
            raw.at[d, t] if d in raw.index and t in raw.columns else np.nan
            for t, d in zip(s.ticker, s.entry, strict=True)
        ]
        s = s.dropna(subset=["rel"])
        by = {}
        for sig in ("bullish", "bearish"):
            x = s.loc[s.signal == sig, "rel"].to_numpy()
            lo, hi = _boot_ci(x)
            hit = float((x > 0).mean() if sig == "bullish" else (x < 0).mean()) if len(x) else None
            rows.append(
                {
                    "horizon": h,
                    "signal": sig,
                    "n": int(len(x)),
                    "mean_rel": float(x.mean()) if len(x) else None,
                    "median_rel": float(np.median(x)) if len(x) else None,
                    "ci_low": lo if len(x) > 1 else None,
                    "ci_high": hi if len(x) > 1 else None,
                    "hit_rate": hit,
                    "mean_raw": float(s.loc[s.signal == sig, "raw"].mean()) if len(x) else None,
                }
            )
            by[sig] = x
        lo, hi = _boot_diff_ci(by["bullish"], by["bearish"])
        spreads.append(
            {
                "horizon": h,
                "spread": float(by["bullish"].mean() - by["bearish"].mean())
                if len(by["bullish"]) and len(by["bearish"])
                else None,
                "ci_low": lo,
                "ci_high": hi,
            }
        )
    clean = lambda v: None if isinstance(v, float) and np.isnan(v) else v  # noqa: E731
    return {
        "unit": "company-day",
        "benchmark": "QQQ",
        "horizons": list(HORIZONS),
        "by_signal": [{k: clean(v) for k, v in r.items()} for r in rows],
        "spread": [{k: clean(v) for k, v in r.items()} for r in spreads],
        "n_company_days": int(len(signals)),
        "n_mixed": int((signals.signal == "mixed").sum()),
    }
