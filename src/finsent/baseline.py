"""TF-IDF + logistic regression baseline. Train with:

    python -m finsent.baseline data/sample.jsonl --out models/baseline.joblib
"""
from __future__ import annotations

import argparse
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.pipeline import Pipeline

from finsent import LABELS
from finsent.data import load_jsonl, time_split, to_frame


def build_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("data", type=Path)
    ap.add_argument("--out", type=Path, default=Path("models/baseline.joblib"))
    ap.add_argument("--test-frac", type=float, default=0.2)
    args = ap.parse_args()

    df = to_frame(load_jsonl(args.data))
    train, test = time_split(df, args.test_frac)

    model = build_pipeline().fit(train["marked_text"], train["label"])
    preds = model.predict(test["marked_text"])
    print(classification_report(test["label"], preds, labels=list(LABELS), zero_division=0))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, args.out)
    print(f"saved -> {args.out}")


if __name__ == "__main__":
    main()
