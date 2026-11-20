"""Deduplicate repeated and syndicated news.

1. Exact duplicates (same canonical URL) are dropped.
2. Near duplicates (same headline fingerprint within `window`) are kept but point to the
   earliest copy via `duplicate_of`, so aggregation counts one story once.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Article:
    key: str  # canonical URL hash
    fingerprint: str
    published_at: datetime
    duplicate_of: str | None = None


def dedupe(articles: list[Article], window: timedelta = timedelta(hours=72)) -> list[Article]:
    seen_urls: set[str] = set()
    originals: dict[str, Article] = {}
    out = []
    for a in sorted(articles, key=lambda x: x.published_at):
        if a.key in seen_urls:
            continue
        seen_urls.add(a.key)
        first = originals.get(a.fingerprint)
        if first is not None and a.published_at - first.published_at <= window:
            a.duplicate_of = first.key
        else:
            originals[a.fingerprint] = a
        out.append(a)
    return out
