"""Classification metrics against the manually labelled evaluation set.

Gold labels come from a blind human labeller (the model's output was hidden). Gold "unclear"
maps to `insufficient_evidence`; gold "not_about" marks an entity-linking error and is excluded
from sentiment metrics (reported separately as linking precision).

Nothing here was tuned on the evaluation set: the decision thresholds were fixed before any
label existed. Results are still reported for the earlier and later halves of the set (by
publication time) to show whether performance is stable over time.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

CLASSES = ["bullish", "bearish", "neutral", "insufficient_evidence"]
GOLD_MAP = {
    "bullish": "bullish",
    "bearish": "bearish",
    "neutral": "neutral",
    "unclear": "insufficient_evidence",
}
RAW_MAP = {"positive": "bullish", "negative": "bearish", "neutral": "neutral"}


def scores(gold: pd.Series, pred: pd.Series) -> dict:
    p, r, f, s = precision_recall_fscore_support(gold, pred, labels=CLASSES, zero_division=0)
    per = {
        c: {
            "precision": float(p[i]),
            "recall": float(r[i]),
            "f1": float(f[i]),
            "support": int(s[i]),
        }
        for i, c in enumerate(CLASSES)
    }
    present = [c for c in CLASSES if per[c]["support"] > 0]
    return {
        "n": int(len(gold)),
        "accuracy": float((gold.to_numpy() == pred.to_numpy()).mean()) if len(gold) else None,
        "macro_f1": float(np.mean([per[c]["f1"] for c in present])) if present else None,
        "per_class": per,
    }


def bootstrap_ci(gold: pd.Series, pred: pd.Series, reps: int = 1000, seed: int = 3) -> dict:
    rng = np.random.default_rng(seed)
    g, p = gold.to_numpy(), pred.to_numpy()
    accs, f1s = [], []
    for _ in range(reps):
        i = rng.integers(0, len(g), len(g))
        sc = scores(pd.Series(g[i]), pd.Series(p[i]))
        accs.append(sc["accuracy"])
        f1s.append(sc["macro_f1"])
    q = lambda x: [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]  # noqa: E731
    return {"accuracy": q(accs), "macro_f1": q(f1s)}


def raw_argmax(df: pd.DataFrame) -> pd.Series:
    """FinBERT's top class with no abstention rule (ablation of the decision thresholds)."""
    probs = df[["p_positive", "p_negative", "p_neutral"]].to_numpy()
    names = np.array(["positive", "negative", "neutral"])
    return pd.Series([RAW_MAP[n] for n in names[probs.argmax(axis=1)]], index=df.index)


def evaluate(df: pd.DataFrame) -> dict:
    """df columns: gold (labeller's raw label), label (model), p_positive, p_negative,
    p_neutral, published_at, headline, ticker, needs_review."""
    linking = {
        "n": int(len(df)),
        "not_about": int((df.gold == "not_about").sum()),
        "precision": float(1 - (df.gold == "not_about").mean()) if len(df) else None,
    }
    d = df[df.gold != "not_about"].copy()
    d["gold4"] = d.gold.map(GOLD_MAP)
    gold = d.gold4

    systems = {
        "finbert_evidence_v1": d.label,
        "finbert_raw_argmax": raw_argmax(d),
        "majority_class": pd.Series(gold.mode().iloc[0] if len(gold) else "neutral", index=d.index),
    }
    results = {}
    for name, pred in systems.items():
        results[name] = {**scores(gold, pred), "ci95": bootstrap_ci(gold, pred)}
    results["hybrid_finbert_claude"] = {
        "status": "not_run",
        "reason": "Claude review is implemented but disabled in this $0-budget snapshot.",
    }

    cm = confusion_matrix(gold, d.label, labels=CLASSES)
    d = d.sort_values("published_at")
    half = len(d) // 2
    periods = {}
    for name, part in (("earlier_half", d.iloc[:half]), ("later_half", d.iloc[half:])):
        periods[name] = {
            "from": str(part.published_at.min()),
            "to": str(part.published_at.max()),
            **scores(part.gold4, part.label),
        }

    def examples(mask, k=8):
        rows = d[mask].head(k)
        return [
            {
                "ticker": r.ticker,
                "headline": r.headline,
                "model": r.label,
                "human": r.gold4,
                "confidence": float(r.confidence) if "confidence" in d else None,
            }
            for r in rows.itertuples()
        ]

    directional = d.label.isin(["bullish", "bearish"])
    errors = {
        "false_directional": examples(directional & (d.label != d.gold4)),
        "missed_directional": examples(d.gold4.isin(["bullish", "bearish"]) & (d.label != d.gold4)),
        "ambiguous": examples(d.gold4.eq("insufficient_evidence")),
    }
    return {
        "systems": results,
        "confusion_matrix": {"labels": CLASSES, "rows_gold_cols_pred": cm.tolist()},
        "periods": periods,
        "linking": linking,
        "label_distribution": {
            "human": {c: int((gold == c).sum()) for c in CLASSES},
            "model": {c: int((d.label == c).sum()) for c in CLASSES},
        },
        "errors": errors,
    }
