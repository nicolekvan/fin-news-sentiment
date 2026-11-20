from datetime import UTC, datetime, timedelta

import pandas as pd

from marketlens.aggregate import aggregate_at

AS_OF = pd.Timestamp(datetime(2026, 11, 10, 21, tzinfo=UTC))


def _row(story, hours_ago, pos, neg, label="bullish", review=False, rel=1.0, conf=0.9):
    return {
        "story_id": story,
        "published_at": AS_OF - timedelta(hours=hours_ago),
        "p_positive": pos,
        "p_negative": neg,
        "relevance": rel,
        "confidence": conf,
        "label": label,
        "needs_review": review,
    }


def test_bullish_with_enough_stories():
    df = pd.DataFrame([_row(i, 10 * i + 1, 0.9, 0.05) for i in range(4)])
    r = aggregate_at(df, AS_OF)
    assert r["label"] == "bullish" and r["n_unique_stories"] == 4 and r["score"] > 0.8


def test_no_look_ahead():
    df = pd.DataFrame(
        [_row(i, 5, 0.9, 0.05) for i in range(3)] + [_row(9, -2, 0.0, 0.99, "bearish")]
    )  # published after as_of
    r = aggregate_at(df, AS_OF)
    assert r["n_articles"] == 3 and r["label"] == "bullish"


def test_syndicated_copies_count_once():
    df = pd.DataFrame(
        [_row(1, 5, 0.05, 0.9, "bearish")] * 10 + [_row(2, 5, 0.9, 0.05), _row(3, 5, 0.9, 0.05)]
    )
    r = aggregate_at(df, AS_OF)
    assert r["n_unique_stories"] == 3 and r["score"] > 0  # 2 positive stories outweigh 1


def test_too_few_stories_is_insufficient_evidence():
    r = aggregate_at(pd.DataFrame([_row(1, 5, 0.95, 0.01)]), AS_OF)
    assert r["label"] == "insufficient_evidence"


def test_review_and_insufficient_excluded_and_old_news_ignored():
    df = pd.DataFrame(
        [
            _row(1, 5, 0.9, 0.05, review=True),
            _row(2, 5, 0.4, 0.4, label="insufficient_evidence"),
            _row(3, 24 * 20, 0.9, 0.05),  # outside 14-day lookback
        ]
    )
    assert aggregate_at(df, AS_OF)["n_articles"] == 0


def test_recency_weighting():
    df = pd.DataFrame(
        [_row(1, 1, 0.9, 0.05), _row(2, 300, 0.05, 0.9, "bearish"), _row(3, 2, 0.5, 0.3)]
    )
    assert aggregate_at(df, AS_OF)["score"] > 0.3
