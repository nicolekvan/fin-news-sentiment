"""Chronological splits. Never split news randomly: stories are autocorrelated and
syndicated copies would leak from train into test."""

from __future__ import annotations

import pandas as pd


def time_split(
    df: pd.DataFrame, test_frac: float = 0.2, time_col: str = "published_at"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.sort_values(time_col).reset_index(drop=True)
    cut = int(len(df) * (1 - test_frac))
    return df.iloc[:cut], df.iloc[cut:]
