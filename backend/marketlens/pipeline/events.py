"""Rule-based event types (transparent; first matching rule wins)."""

from __future__ import annotations

import re

_RULES = [
    (
        "earnings",
        r"\b(earnings|quarterly results|EPS|revenue (beat|miss)|beats? estimates|"
        r"misses? estimates|Q[1-4] results)\b",
    ),
    ("guidance", r"\b(guidance|outlook|forecast)\b"),
    (
        "analyst_rating",
        r"\b(upgrade[sd]?|downgrade[sd]?|price target|initiates? coverage|"
        r"overweight|underweight|outperform)\b",
    ),
    ("mergers_acquisitions", r"\b(acqui(re|res|red|sition)|merger|takeover|buyout|stake in)\b"),
    (
        "legal_regulatory",
        r"\b(lawsuit|antitrust|probe|investigation|regulator|FTC|DOJ|SEC "
        r"charges|fine[sd]?|export (controls|restrictions|curbs))\b",
    ),
    ("product", r"\b(launch(es|ed)?|unveil(s|ed)?|new chip|release[sd]?|announce[sd]? new)\b"),
    ("partnership_contract", r"\b(partnership|partners with|contract|deal with|agreement)\b"),
    ("management", r"\b(CEO|CFO|chief executive|steps down|resign(s|ed)?|appoint(s|ed)?)\b"),
    ("capital_return", r"\b(dividend|buyback|share repurchase)\b"),
]
_COMPILED = [(name, re.compile(rx, re.IGNORECASE)) for name, rx in _RULES]


def classify_event(text: str) -> str:
    for name, rx in _COMPILED:
        if rx.search(text):
            return name
    return "other"
