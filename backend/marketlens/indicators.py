"""Technical indicators computed locally with the `ta` library (no indicator API calls).

Standard parameters: SMA 20/50/200, EMA 12/26, RSI 14 (Wilder), MACD 12/26/9,
Bollinger Bands 20/2, ATR 14. Values are NaN until enough history exists (warm-up).
"""

from __future__ import annotations

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands

INDICATOR_COLUMNS = [
    "sma_20",
    "sma_50",
    "sma_200",
    "ema_12",
    "ema_26",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "bb_upper",
    "bb_mid",
    "bb_lower",
    "atr_14",
]


def compute_indicators(prices: pd.DataFrame) -> pd.DataFrame:
    """prices: trade_date, high, low, close (any order). Returns trade_date + indicators."""
    df = prices.sort_values("trade_date").reset_index(drop=True)
    close, high, low = df["close"].astype(float), df["high"].astype(float), df["low"].astype(float)
    out = pd.DataFrame({"trade_date": df["trade_date"]})
    for n in (20, 50, 200):
        out[f"sma_{n}"] = SMAIndicator(close, n, fillna=False).sma_indicator()
    for n in (12, 26):
        out[f"ema_{n}"] = EMAIndicator(close, n, fillna=False).ema_indicator()
    out["rsi_14"] = RSIIndicator(close, 14, fillna=False).rsi()
    macd = MACD(close, window_slow=26, window_fast=12, window_sign=9, fillna=False)
    out["macd"], out["macd_signal"], out["macd_hist"] = (
        macd.macd(),
        macd.macd_signal(),
        macd.macd_diff(),
    )
    bb = BollingerBands(close, window=20, window_dev=2, fillna=False)
    out["bb_upper"], out["bb_mid"], out["bb_lower"] = (
        bb.bollinger_hband(),
        bb.bollinger_mavg(),
        bb.bollinger_lband(),
    )
    atr = AverageTrueRange(high, low, close, window=14, fillna=False).average_true_range()
    # ta returns 0.0 (not NaN) for ATR during warm-up; store those as missing.
    atr.iloc[:14] = float("nan")
    out["atr_14"] = atr
    return out
