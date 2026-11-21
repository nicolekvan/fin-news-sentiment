"""Link articles to universe companies and extract company-specific passages.

Linking uses ticker mappings and company aliases (case-sensitive, word boundaries). An
article is linked only if the company is named in its headline or summary; a provider's
ticker tag alone is not enough (Finnhub tags many market-wide stories). Named-entity
recognition is not used in this version.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from marketlens.universe import Company

_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[\"'“A-Z0-9$])")
MAX_PASSAGE_CHARS = 700


@dataclass(frozen=True)
class Link:
    ticker: str
    relevance: float  # 1.0 named in headline, 0.7 named only in summary
    match_method: str  # 'alias' or 'ticker'
    passage: str  # only sentences that mention the company
    other_companies: tuple[str, ...]  # other universe companies named in the same passage


def company_pattern(c: Company) -> re.Pattern:
    names = sorted({c.name, *c.aliases} - {""}, key=len, reverse=True)
    alias = "|".join(re.escape(n) for n in names)
    ticker = re.escape(c.ticker)
    if c.bare_ticker:
        # $NVDA, (NVDA), NASDAQ:NVDA, or the bare upper-case ticker
        tick = rf"\$?\b{ticker}\b"
    else:
        # word-like tickers (NOW, NET, APP...) only count in explicit ticker notation
        tick = rf"(?:\${ticker}|\({ticker}\)|(?:NYSE|NASDAQ|Nasdaq)\s*:\s*{ticker})\b"
    return re.compile(rf"(?P<alias>\b(?:{alias})\b)|(?P<ticker>{tick})")


def split_sentences(text: str) -> list[str]:
    """Split on line breaks (headline/summary boundary) and on sentence punctuation."""
    out = []
    for line in text.split("\n"):
        out.extend(s.strip() for s in _SENTENCE.split(line) if s.strip())
    return out


def link_article(
    headline: str, summary: str, companies: list[Company], patterns: dict[str, re.Pattern]
) -> list[Link]:
    sentences = [headline] + [s for s in split_sentences(summary) if s != headline]
    mentions = {
        c.ticker: [i for i, s in enumerate(sentences) if patterns[c.ticker].search(s)]
        for c in companies
    }
    links = []
    for c in companies:
        idx = mentions[c.ticker]
        if not idx:
            continue
        chosen = [sentences[i] for i in idx]
        # newline keeps the (often unpunctuated) headline a separate sentence
        passage = "\n".join(chosen)[:MAX_PASSAGE_CHARS]
        m = patterns[c.ticker].search(" ".join(chosen))
        others = tuple(
            o.ticker
            for o in companies
            if o.ticker != c.ticker and set(mentions[o.ticker]) & set(idx)
        )
        links.append(
            Link(
                ticker=c.ticker,
                relevance=1.0 if 0 in idx else 0.7,
                match_method="alias" if m and m.group("alias") else "ticker",
                passage=passage,
                other_companies=others,
            )
        )
    return links
