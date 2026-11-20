"""Company-level sentiment aggregation (transparent and versioned).

For a company at time T (end of each trading day, 21:00 UTC), using only articles published
before T (no look-ahead) within the last LOOKBACK_DAYS:

  1. Drop `insufficient_evidence` and `needs_review` predictions.
  2. Collapse syndicated copies: one story = an article and its duplicates. Story score is the
     mean of s = P(positive) - P(negative); story weight is the max of the copies' weights.
  3. weight = relevance * confidence * 0.5 ** (age_hours / HALF_LIFE_HOURS)
  4. score = sum(w * s) / sum(w)          (in [-1, 1])
  5. label: < MIN_STORIES stories -> insufficient_evidence; score >= +T -> bullish;
     score <= -T -> bearish; otherwise neutral.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

METHOD_VERSION = "agg-v1"
CONFIG = {"lookback_days": 14, "half_life_hours": 72, "threshold": 0.15, "min_stories": 3}
AS_OF_TIME = time(21, 0)  # after the 16:00 ET close (20:00/21:00 UTC)


def aggregate_at(preds: pd.DataFrame, as_of: datetime) -> dict:
    """preds columns: story_id, published_at (UTC), p_positive, p_negative, relevance,
    confidence, label, needs_review."""
    lo = as_of - timedelta(days=CONFIG["lookback_days"])
    w = preds[
        (preds.published_at < as_of)
        & (preds.published_at >= lo)
        & (preds.label != "insufficient_evidence")
        & (~preds.needs_review)
    ].copy()
    if w.empty:
        return {
            "score": 0.0,
            "label": "insufficient_evidence",
            "n_articles": 0,
            "n_unique_stories": 0,
        }
    age_h = (as_of - w.published_at).dt.total_seconds() / 3600
    w["s"] = w.p_positive - w.p_negative
    w["w"] = w.relevance * w.confidence * np.power(0.5, age_h / CONFIG["half_life_hours"])
    stories = w.groupby("story_id").agg(s=("s", "mean"), w=("w", "max"))
    score = float((stories.s * stories.w).sum() / stories.w.sum())
    n = len(stories)
    if n < CONFIG["min_stories"]:
        label = "insufficient_evidence"
    elif score >= CONFIG["threshold"]:
        label = "bullish"
    elif score <= -CONFIG["threshold"]:
        label = "bearish"
    else:
        label = "neutral"
    return {
        "score": round(max(-1.0, min(1.0, score)), 6),
        "label": label,
        "n_articles": len(w),
        "n_unique_stories": n,
    }


def daily_aggregates(preds: pd.DataFrame, days: list[date]) -> list[dict]:
    out = []
    for d in days:
        as_of = pd.Timestamp(datetime.combine(d, AS_OF_TIME), tz="UTC")
        out.append({"as_of": as_of.to_pydatetime(), **aggregate_at(preds, as_of)})
    return out
