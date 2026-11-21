import pandas as pd
import pytest

from marketlens.evaluation.metrics import evaluate, scores


def _df(rows):
    out = pd.DataFrame(rows, columns=["gold", "label", "p_positive", "p_negative", "p_neutral"])
    out["published_at"] = pd.date_range("2026-09-01", periods=len(out), freq="D", tz="UTC")
    out["headline"] = "h"
    out["ticker"] = "AAA"
    out["needs_review"] = False
    out["confidence"] = 0.9
    return out


def test_scores_perfect_and_macro_over_present_classes():
    g = pd.Series(["bullish", "bearish", "neutral"])
    s = scores(g, g)
    assert s["accuracy"] == 1 and s["macro_f1"] == 1
    assert s["per_class"]["insufficient_evidence"]["support"] == 0


def test_evaluate_maps_gold_and_excludes_linking_errors():
    df = _df(
        [
            ("bullish", "bullish", 0.9, 0.05, 0.05),
            ("bearish", "bullish", 0.8, 0.1, 0.1),
            ("unclear", "insufficient_evidence", 0.4, 0.4, 0.2),
            ("neutral", "neutral", 0.1, 0.1, 0.8),
            ("not_about", "bullish", 0.9, 0.05, 0.05),
        ]
    )
    r = evaluate(df)
    assert r["linking"]["not_about"] == 1 and r["linking"]["precision"] == pytest.approx(0.8)
    sys = r["systems"]["finbert_evidence_v1"]
    assert sys["n"] == 4 and sys["accuracy"] == pytest.approx(0.75)
    # raw argmax cannot abstain, so it misses the ambiguous item
    assert r["systems"]["finbert_raw_argmax"]["accuracy"] == pytest.approx(0.5)
    assert r["systems"]["hybrid_finbert_claude"]["status"] == "not_run"
    cm = r["confusion_matrix"]["rows_gold_cols_pred"]
    assert cm[1][0] == 1  # gold bearish predicted bullish
    assert len(r["errors"]["false_directional"]) == 1
    lo, hi = sys["ci95"]["accuracy"]
    assert 0 <= lo <= sys["accuracy"] <= hi <= 1
