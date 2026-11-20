from marketlens.demo import DEMO_PUBLISHER, demo_news, demo_prices


def test_demo_prices_deterministic_and_valid():
    a, b = demo_prices("NVDA"), demo_prices("NVDA")
    assert a.equals(b)
    assert not a.equals(demo_prices("AAPL"))
    assert (a.high >= a[["open", "close"]].max(axis=1)).all()
    assert (a.low <= a[["open", "close"]].min(axis=1)).all()
    assert (a.close > 0).all() and (a.volume > 0).all()


def test_demo_news_is_clearly_labelled():
    df = demo_news("NVDA", "NVIDIA")
    assert df.headline.str.startswith("[DEMO]").all()
    assert (df.source_name == DEMO_PUBLISHER).all()
    assert df.url.str.startswith("https://example.com/demo/").all()
