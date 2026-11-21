"""Convert labels exported from the labelling page's database into the committed CSV.

    python -m marketlens.evaluation.import_labels <dir with labels/*.json> \
        --out ../data/eval/labels_v1.csv

Only ids and labels are written (article_id, ticker, label, labeled_at): no article text,
so the file is safe to commit. Notes typed in the labeller are not exported.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

VALID = {"bullish", "bearish", "neutral", "unclear", "not_about"}
ID = re.compile(r"^a(\d+)-([A-Z.]{1,10})$")


def convert(src: Path, out: Path) -> int:
    rows = []
    for f in sorted(src.rglob("*.json")):
        doc_id = f.stem
        m = ID.match(doc_id)
        body = json.loads(f.read_text())
        data = body.get("data", body)
        if not m or data.get("label") not in VALID:
            raise ValueError(f"unexpected label document {f.name}")
        rows.append(
            {
                "article_id": int(m.group(1)),
                "ticker": m.group(2),
                "label": data["label"],
                "labeled_at": data.get("labeled_at", ""),
            }
        )
    rows.sort(key=lambda r: (r["article_id"], r["ticker"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["article_id", "ticker", "label", "labeled_at"])
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    print(f"{convert(a.src, a.out)} labels -> {a.out}")


if __name__ == "__main__":
    main()
