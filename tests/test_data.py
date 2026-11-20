from pathlib import Path

from finsent.data import Example, load_jsonl, mark_target, time_split, to_frame

SAMPLE = Path(__file__).parent.parent / "data" / "sample.jsonl"


def test_mark_target_only_marks_target_company():
    ex = Example(id="x", text="Boeing beats Lockheed Martin; Lockheed shares fall.",
                 ticker="LMT", company="Lockheed Martin", aliases=["Lockheed"])
    out = mark_target(ex)
    assert out.count("[TGT]") == 2
    assert "[TGT] Boeing" not in out


def test_same_article_can_have_different_labels_per_company():
    df = to_frame(load_jsonl(SAMPLE))
    boeing_story = df[df["text"].str.contains("Air Force contract")]
    assert set(boeing_story["label"]) == {"bullish", "bearish"}
    assert boeing_story["marked_text"].nunique() == 2


def test_time_split_has_no_lookahead():
    train, test = time_split(to_frame(load_jsonl(SAMPLE)), test_frac=0.3)
    assert train["published_at"].max() <= test["published_at"].min()
