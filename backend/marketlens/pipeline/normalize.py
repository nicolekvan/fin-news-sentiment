"""Normalization: clean text, canonical URLs, content fingerprints. All times UTC."""

from __future__ import annotations

import hashlib
import html
import re
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING = re.compile(r"^(utm_|fbclid$|gclid$|mc_|ref$|cmpid$|ocid$)")
_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_SOURCE_SUFFIX = re.compile(r"\s+[-|–—]\s+[A-Z][\w .&']{1,40}$")
_NON_ALNUM = re.compile(r"[^a-z0-9 ]+")


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    return _WS.sub(" ", _TAGS.sub(" ", html.unescape(text))).strip()


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not _TRACKING.match(k.lower())
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def url_hash(url: str) -> str:
    return hashlib.sha256(canonical_url(url).encode()).hexdigest()


def headline_fingerprint(headline: str) -> str:
    """Same story syndicated by several outlets -> same fingerprint."""
    h = _SOURCE_SUFFIX.sub("", clean_text(headline)).lower()
    h = _WS.sub(" ", _NON_ALNUM.sub(" ", h)).strip()
    return hashlib.sha1(h.encode()).hexdigest()


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("naive datetime: source timezone unknown")
    return dt.astimezone(UTC)
