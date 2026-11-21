"""Run the evaluations and store them in model_evaluations.

    python -m marketlens.jobs.evaluate [--labels ../data/eval/labels_v1.csv]

1. Forward returns after bullish / bearish company-days (always; needs only prices + preds).
2. Classification metrics against the human labels (when a labels file is given).
   The labels CSV holds only ids and labels (article_id, ticker, label, labeled_at), no text.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from marketlens.db import get_engine
from marketlens.db.repository import log_finish, log_start
from marketlens.evaluation.metrics import evaluate
from marketlens.evaluation.returns import company_day_signals, forward_returns, summarize
from marketlens.jobs.news import MODEL_NAME, MODEL_VERSION

LABELER = "project-owner"
EVAL_DATASET = "manual-eval-v1"
RETURNS_DATASET = "forward-returns-v1"

PREDS_SQL = """
select a.id as article_id, c.ticker, a.published_at, a.duplicate_of, a.headline,
       p.label, p.needs_review, p.confidence, p.p_positive, p.p_negative, p.p_neutral
from sentiment_predictions p
join news_articles a on a.id = p.article_id
join companies c on c.id = p.company_id
join model_versions mv on mv.id = p.model_version_id
where mv.name = :n and mv.version = :v
"""


def _model_version_id(conn) -> int:
    return conn.execute(
        text("select id from model_versions where name = :n and version = :v"),
        {"n": MODEL_NAME, "v": MODEL_VERSION},
    ).scalar_one()


def _store(conn, mv_id: int, dataset: str, split: str, metrics: dict, cm: dict) -> None:
    conn.execute(
        text("delete from model_evaluations where model_version_id = :m and dataset = :d"),
        {"m": mv_id, "d": dataset},
    )
    conn.execute(
        text("""insert into model_evaluations (model_version_id, dataset, split, metrics,
                confusion_matrix) values (:m, :d, :s, cast(:x as jsonb), cast(:c as jsonb))"""),
        {"m": mv_id, "d": dataset, "s": split, "x": json.dumps(metrics), "c": json.dumps(cm)},
    )


def run(labels_path: Path | None = None, engine=None) -> dict:
    engine = engine or get_engine()
    with engine.begin() as conn:
        log_id = log_start(conn, "evaluate", None)
        mv_id = _model_version_id(conn)
        preds = pd.read_sql(text(PREDS_SQL), conn, params={"n": MODEL_NAME, "v": MODEL_VERSION})
        preds["published_at"] = pd.to_datetime(preds.published_at, utc=True)
        for col in ("confidence", "p_positive", "p_negative", "p_neutral"):
            preds[col] = preds[col].astype(float)
        prices = pd.read_sql(
            text(
                "select c.ticker, p.trade_date, p.close from stock_prices p "
                "join companies c on c.id = p.company_id"
            ),
            conn,
        )
        closes = prices.pivot(index="trade_date", columns="ticker", values="close").astype(float)
        closes.index = pd.to_datetime(closes.index)
        signals = company_day_signals(preds, closes.index)
        returns = summarize(signals, forward_returns(closes))
        _store(conn, mv_id, RETURNS_DATASET, "all", returns, {})
        out = {"forward_returns": returns}

        if labels_path is not None:
            labels = pd.read_csv(labels_path)
            labels["article_id"] = labels.article_id.astype(int)
            df = labels.merge(preds, on=["article_id", "ticker"], how="inner")
            if len(df) != len(labels):
                raise ValueError(f"{len(labels) - len(df)} labelled items have no prediction")
            df = df.rename(columns={"label_x": "gold", "label_y": "label"})
            ids = {r.ticker: r.id for r in conn.execute(text("select id, ticker from companies"))}
            conn.execute(text("delete from evaluation_labels where labeler = :l"), {"l": LABELER})
            gold_db = df[df.gold != "not_about"]
            conn.execute(
                text("""insert into evaluation_labels (article_id, company_id, label, labeler,
                        labeled_at) values (:a, :c, :l, :who, :t)"""),
                [
                    {
                        "a": int(r.article_id),
                        "c": ids[r.ticker],
                        "l": "insufficient_evidence" if r.gold == "unclear" else r.gold,
                        "who": LABELER,
                        "t": r.labeled_at,
                    }
                    for r in gold_db.itertuples()
                ],
            )
            result = evaluate(df)
            result["n_labelled"] = int(len(labels))
            _store(conn, mv_id, EVAL_DATASET, "all", result, result["confusion_matrix"])
            out["classification"] = result
        log_finish(conn, log_id, "success", len(out), 0)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", type=Path)
    args = ap.parse_args()
    out = run(args.labels)
    fr = out["forward_returns"]
    print(f"forward returns: {fr['n_company_days']} company-days")
    for r in fr["by_signal"]:
        if r["mean_rel"] is not None:
            print(
                f"  {r['horizon']:>2}d {r['signal']:<8} n={r['n']:<4} mean vs QQQ "
                f"{r['mean_rel']:+.2%}  CI [{r['ci_low'] or 0:+.2%}, {r['ci_high'] or 0:+.2%}]"
            )
    if "classification" in out:
        s = out["classification"]["systems"]["finbert_evidence_v1"]
        print(
            f"classification: n={s['n']} accuracy={s['accuracy']:.3f} macro-F1={s['macro_f1']:.3f}"
        )


if __name__ == "__main__":
    main()
