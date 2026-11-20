"""Loading examples and marking the target company in the text.

Each example is one (article, company) pair, because a single article can be
bullish for one company and bearish for another ("X wins contract from Y").
Expected JSONL schema, one object per line:

    {"id": "...", "published_at": "2024-03-01T14:30:00Z",
     "text": "headline + body", "ticker": "AAPL",
     "company": "Apple", "aliases": ["Apple Inc", "iPhone maker"],
     "label": "bullish"}
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from finsent import LABELS

TARGET_OPEN, TARGET_CLOSE = "[TGT]", "[/TGT]"


@dataclass
class Example:
    id: str
    text: str
    ticker: str
    company: str
    label: str | None = None
    published_at: str | None = None
    aliases: list[str] = field(default_factory=list)


def load_jsonl(path: str | Path) -> list[Example]:
    examples = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            ex = Example(**row)
            if ex.label is not None and ex.label not in LABELS:
                raise ValueError(f"{path}:{line_no}: unknown label {ex.label!r}")
            examples.append(ex)
    return examples


def mark_target(ex: Example) -> str:
    """Wrap every mention of the target company (name, aliases, ticker) in markers
    so the model knows *which* company to judge."""
    names = sorted({ex.company, ex.ticker, *ex.aliases} - {""}, key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")\b")
    return pattern.sub(lambda m: f"{TARGET_OPEN} {m.group(0)} {TARGET_CLOSE}", ex.text)


def to_frame(examples: list[Example]) -> pd.DataFrame:
    df = pd.DataFrame([vars(e) for e in examples])
    df["marked_text"] = [mark_target(e) for e in examples]
    return df


def time_split(df: pd.DataFrame, test_frac: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split by publication time, never randomly: news is autocorrelated and a
    random split leaks near-duplicate stories into the test set."""
    df = df.sort_values("published_at").reset_index(drop=True)
    cut = int(len(df) * (1 - test_frac))
    return df.iloc[:cut], df.iloc[cut:]
