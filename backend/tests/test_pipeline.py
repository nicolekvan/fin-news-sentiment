from datetime import UTC, datetime, timedelta

import pytest

from marketlens.models.decision import decide
from marketlens.models.finbert import Probs
from marketlens.pipeline.dedupe import Article, dedupe
from marketlens.pipeline.entities import company_pattern, link_article, split_sentences
from marketlens.pipeline.events import classify_event
from marketlens.pipeline.normalize import (
    canonical_url,
    clean_text,
    headline_fingerprint,
    to_utc,
    url_hash,
)
from marketlens.universe import load_universe

COMPANIES = [c for c in load_universe(dev_only=True) if not c.is_benchmark]
PATTERNS = {c.ticker: company_pattern(c) for c in COMPANIES}
T0 = datetime(2026, 11, 1, 14, 0, tzinfo=UTC)


def test_canonical_url_strips_tracking_and_fragments():
    a = "HTTPS://News.Example.com/story/1/?utm_source=x&id=7#comments"
    assert canonical_url(a) == "https://news.example.com/story/1?id=7"
    assert url_hash(a) == url_hash("https://news.example.com/story/1?id=7")


def test_syndicated_headlines_share_fingerprint():
    assert headline_fingerprint("Nvidia beats estimates - Reuters") == headline_fingerprint(
        "NVIDIA BEATS ESTIMATES!"
    )


def test_clean_text_and_utc():
    assert clean_text("<b>AMD&amp;Intel</b>\n  rally") == "AMD&Intel rally"
    with pytest.raises(ValueError):
        to_utc(datetime(2026, 1, 1))


def test_dedupe_exact_and_near_duplicates():
    arts = [
        Article("u1", "f1", T0),
        Article("u1", "f1", T0),  # exact duplicate URL -> dropped
        Article("u2", "f1", T0 + timedelta(hours=5)),  # syndicated copy -> points to u1
        Article("u3", "f1", T0 + timedelta(days=10)),  # same headline much later -> new story
    ]
    out = dedupe(arts)
    assert [a.key for a in out] == ["u1", "u2", "u3"]
    assert [a.duplicate_of for a in out] == [None, "u1", None]


def test_each_company_gets_its_own_passage():
    links = link_article(
        "Broadcom wins custom chip order",
        "Broadcom will supply the parts. Shares of AMD fell after it lost the bid.",
        COMPANIES,
        PATTERNS,
    )
    by = {ln.ticker: ln for ln in links}
    assert set(by) == {"AVGO", "AMD"}
    assert "AMD" not in by["AVGO"].passage and "Broadcom" not in by["AMD"].passage
    assert by["AVGO"].relevance == 1.0 and by["AMD"].relevance == 0.7
    assert by["AVGO"].other_companies == ()


def test_unrelated_and_lowercase_words_not_linked():
    assert link_article("A meta-analysis of apple orchards", "", COMPANIES, PATTERNS) == []


def test_ticker_forms_are_linked():
    links = link_article("Why $PLTR and (ORCL) moved today", "", COMPANIES, PATTERNS)
    assert {ln.ticker for ln in links} == {"PLTR", "ORCL"}
    assert all(ln.match_method == "ticker" for ln in links)
    assert links[0].other_companies  # both named in the same sentence


def test_event_rules():
    assert classify_event("Nvidia Q3 results beat estimates") == "earnings"
    assert classify_event("Analyst downgrades Oracle") == "analyst_rating"
    assert classify_event("A quiet day") == "other"


def _p(pos, neg, neu):
    return Probs(pos, neg, neu)


def test_decide_directional_with_verbatim_evidence():
    passage = "Nvidia raised guidance. Nvidia also named a new CFO."
    sents = split_sentences(passage)
    d = decide(
        "Nvidia", passage, _p(0.9, 0.05, 0.05), sents, [_p(0.95, 0, 0.05), _p(0.2, 0.1, 0.7)]
    )
    assert d.label == "bullish" and not d.needs_review
    assert d.evidence_quotes[0] == "Nvidia raised guidance."
    assert all(q in passage for q in d.evidence_quotes)
    assert "not a price forecast" in d.explanation


def test_decide_low_confidence_is_insufficient_evidence():
    d = decide("AMD", "AMD news.", _p(0.45, 0.40, 0.15), ["AMD news."], [_p(0.45, 0.4, 0.15)])
    assert d.label == "insufficient_evidence" and d.needs_review


def test_decide_flags_multi_company_tone():
    s = ["Broadcom beat AMD for the contract."]
    d = decide("AMD", s[0], _p(0.85, 0.1, 0.05), s, [_p(0.85, 0.1, 0.05)], ("AVGO",))
    assert d.needs_review and "AVGO" in d.explanation


def test_unpunctuated_headline_stays_its_own_sentence():
    (link,) = link_article(
        "Lenders balk at Nvidia chips in orbit",
        "Banks raised concerns. Nvidia shares slipped.",
        COMPANIES,
        PATTERNS,
    )
    sents = split_sentences(link.passage)
    assert sents == ["Lenders balk at Nvidia chips in orbit", "Nvidia shares slipped."]
    assert all(s in link.passage for s in sents)
