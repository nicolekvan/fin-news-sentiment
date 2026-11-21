import numpy as np
import pandas as pd

from marketlens.evaluation.returns import (
    company_day_signals,
    entry_dates,
    forward_returns,
    summarize,
)

DAYS = pd.bdate_range("2026-11-02", "2026-11-30")


def test_entry_is_first_close_after_publication():
    pub = pd.Series(
        pd.to_datetime(
            [
                "2026-11-03T14:00:00Z",  # 09:00 ET Tue -> Tue close
                "2026-11-03T21:30:00Z",  # 16:30 ET Tue (after close) -> Wed
                "2026-11-07T15:00:00Z",  # Saturday -> Monday
                "2026-11-03T20:59:00Z",  # 15:59 ET -> same day
            ],
            utc=True,
        )
    )
    got = entry_dates(pub, DAYS)
    assert [d.strftime("%a %d") for d in got] == ["Tue 03", "Wed 04", "Mon 09", "Tue 03"]


def test_forward_returns_relative_to_benchmark():
    closes = pd.DataFrame({"AAA": [100, 110, 121], "QQQ": [100, 105, 105]}, index=DAYS[:3])
    f = forward_returns(closes)
    assert np.isclose(f[1]["raw"].iloc[0]["AAA"], 0.10)
    assert np.isclose(f[1]["rel"].iloc[0]["AAA"], 0.10 - 0.05)
    assert np.isnan(f[5]["rel"].iloc[0]["AAA"])  # window incomplete -> excluded, not guessed


def test_company_day_netting_and_filters():
    preds = pd.DataFrame(
        {
            "ticker": ["AAA"] * 5,
            "published_at": pd.to_datetime(["2026-11-03T14:00:00Z"] * 5, utc=True),
            "label": ["bullish", "bullish", "bearish", "neutral", "bullish"],
            "needs_review": [False, False, False, False, True],
            "duplicate_of": [None, None, None, None, None],
        }
    )
    s = company_day_signals(preds, DAYS)
    assert len(s) == 1 and s.iloc[0].net == 1 and s.iloc[0].signal == "bullish"


def test_summary_uses_only_complete_windows():
    closes = pd.DataFrame({"AAA": np.linspace(100, 130, len(DAYS)), "QQQ": 100.0}, index=DAYS)
    sig = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "entry": [DAYS[0], DAYS[-2]],
            "net": [1, -1],
            "n": [1, 1],
            "signal": ["bullish", "bearish"],
        }
    )
    out = summarize(sig, forward_returns(closes))
    one = {(r["horizon"], r["signal"]): r for r in out["by_signal"]}
    assert one[(1, "bullish")]["n"] == 1 and one[(1, "bullish")]["mean_rel"] > 0
    assert one[(20, "bearish")]["n"] == 0  # too close to the end of the data
