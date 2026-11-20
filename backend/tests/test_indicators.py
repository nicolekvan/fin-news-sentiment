import numpy as np
import pandas as pd
import pytest

from marketlens.demo import demo_prices
from marketlens.indicators import compute_indicators


@pytest.fixture(scope="module")
def data():
    p = demo_prices("NVDA", "2025-01-01", "2026-11-20")
    return p, compute_indicators(p)


def _wilder_rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Independent reference implementation (Wilder smoothing)."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss)


def test_sma_matches_rolling_mean(data):
    p, ind = data
    expected = p["close"].rolling(50).mean()
    np.testing.assert_allclose(ind["sma_50"].dropna(), expected.dropna(), rtol=1e-9)
    assert ind["sma_200"].isna().sum() == 199  # warm-up is NaN, not zero


def test_rsi_matches_reference_and_bounds(data):
    p, ind = data
    ref = _wilder_rsi(p["close"].astype(float))
    # Implementations differ only in how the first smoothed value is seeded; the difference
    # decays by 13/14 per bar. The pull fetches 460 days so displayed values are converged.
    np.testing.assert_allclose(ind["rsi_14"].iloc[200:], ref.iloc[200:], rtol=1e-4)
    assert ind["rsi_14"].dropna().between(0, 100).all()


def test_macd_is_ema_difference(data):
    _, ind = data
    np.testing.assert_allclose(
        ind["macd"].dropna(), (ind["ema_12"] - ind["ema_26"]).dropna(), rtol=1e-9
    )
    np.testing.assert_allclose(
        ind["macd_hist"].dropna(), (ind["macd"] - ind["macd_signal"]).dropna(), rtol=1e-9
    )


def test_bollinger_and_atr(data):
    p, ind = data
    np.testing.assert_allclose(ind["bb_mid"].dropna(), ind["sma_20"].dropna(), rtol=1e-9)
    std = p["close"].rolling(20).std(ddof=0)
    np.testing.assert_allclose(
        (ind["bb_upper"] - ind["bb_mid"]).dropna(), (2 * std).dropna(), rtol=1e-9
    )
    assert ind["atr_14"].iloc[:14].isna().all()
    assert (ind["atr_14"].dropna() > 0).all()


def test_unsorted_input_is_handled():
    p = demo_prices("AMD", "2026-01-01", "2026-06-30")
    a = compute_indicators(p)
    b = compute_indicators(p.sample(frac=1, random_state=0))
    pd.testing.assert_frame_equal(a, b)
